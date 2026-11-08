"""CU-12 — Ver mis chats activos y abrir uno. Caso de uso (handler).

RF: RF-CHT-15, RF-CHT-18, RF-CHT-19, RF-CHT-21, RF-CHT-25
- Lista los chats activos del usuario por último mensaje descendente, con indicador de no leídos.
- Abrir un chat no reinicia su conteo de inactividad (RF-CHT-12) y marca los mensajes como leídos.
- EA-04 (Avisar expiración próxima; RF-CHT-12, RF-CHT-14) se calcula al abrir: aviso cuando falta la
  anticipación configurada (inicial 10 min) o menos. Un chat expirado no se abre (RF-CHT-15/25).
- Las imágenes solo se entregan a los participantes de un chat vigente (RNF-SEG-04).
"""
from datetime import datetime, timedelta

from app.shared.domain.contracts import IChatRepository, IClock, IConfigurationProvider, ImageStorage
from app.shared.domain.entities import Chat, ClaveParametro
from app.shared.domain.errors import NoDisponible, NoEncontrado
from app.shared.domain.reglas import minutos_hacia_arriba, segundos_restantes

from .request import (AbrirChatRequest, AvisoExpiracion, ChatDetalleResponse, ChatResumenResponse,
                      ImagenDescargada, MensajeResponse, MisChatsResponse)

MSG_EXPIRADO = "Este chat expiró"  # RF-CHT-25


def url_imagen(chat_id: str, mensaje_id: str) -> str:
    return f"/api/chats/{chat_id}/mensajes/{mensaje_id}/imagen"


class VerMisChatsHandler:
    def __init__(self, chats: IChatRepository, imagenes: ImageStorage, config: IConfigurationProvider,
                 clock: IClock) -> None:
        self._chats = chats
        self._imagenes = imagenes
        self._config = config
        self._clock = clock

    async def handle(self, estudiante_id: str) -> MisChatsResponse:
        ahora = self._clock.ahora()
        chats = await self._chats.listar_activos_por_usuario(estudiante_id, ahora)
        chats = sorted((c for c in chats if c.activo(ahora)), key=lambda c: c.ultima_actividad, reverse=True)
        return MisChatsResponse(ahora=ahora, items=[
            ChatResumenResponse(id=c.id, tipo_publicacion=c.tipo_publicacion, titulo_publicacion=c.titulo_publicacion,
                                nickname_contraparte=c.contraparte(estudiante_id)[1],
                                ultimo_mensaje_en=c.ultima_actividad, fecha_expiracion=c.fecha_expiracion,
                                no_leidos=c.tiene_no_leidos(estudiante_id))
            for c in chats
        ])

    async def abrir(self, estudiante_id: str, chat_id: str, body: AbrirChatRequest | None = None) -> ChatDetalleResponse:
        ahora = self._clock.ahora()
        chat = await self._chat_vigente(estudiante_id, chat_id, ahora)
        mensajes = await self._chats.listar_mensajes(chat.id, body.despues_de if body else None)
        if mensajes or body is None or body.despues_de is None:
            await self._chats.marcar_leido(chat.id, estudiante_id, ahora)  # RF-CHT-21
        return ChatDetalleResponse(
            ahora=ahora, id=chat.id, tipo_publicacion=chat.tipo_publicacion,
            titulo_publicacion=chat.titulo_publicacion, nickname_contraparte=chat.contraparte(estudiante_id)[1],
            fecha_expiracion=chat.fecha_expiracion,
            segundos_restantes=segundos_restantes(chat.fecha_expiracion, ahora),
            aviso=self._calcular_aviso(chat, ahora),
            mensajes=[MensajeResponse(id=m.id, es_propio=m.emisor_id == estudiante_id,
                                      nickname_emisor=m.nickname_emisor, texto=m.texto,
                                      imagen_url=url_imagen(chat.id, m.id) if m.imagen else None,
                                      fecha_envio=m.fecha_envio)
                      for m in mensajes],
        )

    async def imagen(self, estudiante_id: str, chat_id: str, mensaje_id: str) -> ImagenDescargada:
        chat = await self._chat_vigente(estudiante_id, chat_id, self._clock.ahora())
        mensaje = await self._chats.buscar_mensaje(chat.id, mensaje_id)
        contenido = await self._imagenes.leer(mensaje.imagen.referencia) if mensaje and mensaje.imagen else None
        if contenido is None:
            raise NoEncontrado("La imagen no existe", codigo="imagen_inexistente")
        return ImagenDescargada(contenido, mensaje.imagen.mime_type)

    async def _chat_vigente(self, estudiante_id: str, chat_id: str, ahora: datetime) -> Chat:
        chat = await self._chats.buscar_por_id(chat_id)
        if chat is None or estudiante_id not in chat.participantes:
            raise NoEncontrado("El chat no existe", codigo="chat_inexistente")
        if not chat.activo(ahora):
            raise NoDisponible(MSG_EXPIRADO, codigo="chat_expirado")
        return chat

    def _calcular_aviso(self, chat: Chat, ahora: datetime) -> AvisoExpiracion:
        """EA-04 — activo si el tiempo restante es ≤ la anticipación configurada (RF-CFG-05)."""
        restante = chat.fecha_expiracion - ahora
        anticipacion = timedelta(minutes=self._config.entero(ClaveParametro.ANTICIPACION_AVISO_CHAT_MIN))
        minutos = minutos_hacia_arriba(restante)
        if timedelta(0) < restante <= anticipacion:
            return AvisoExpiracion(activo=True, minutos=minutos, mensaje=(
                f"Este chat expira en {minutos} min por inactividad. Envía un mensaje para mantenerlo"))
        return AvisoExpiracion(activo=False, minutos=minutos)
