"""CU-11 — Enviar mensaje en un chat. Caso de uso (handler).

RF: RF-CHT-08–12, RF-CHT-15, RF-CHT-20, RF-CHT-22, RF-CHT-25, RF-CHT-26
Solo los participantes de un chat vigente pueden enviar. Cada mensaje reinicia el conteo de
inactividad: nueva expiración = hora del mensaje + 24 h (RF-CHT-12). El chat se verifica de forma
atómica al registrar el mensaje, por si expira entre la lectura y la escritura.
"""
from app.shared.clock import hora_hhmm
from app.shared.domain.contracts import IChatRepository, IClock, ImageStorage
from app.shared.domain.entities import INACTIVIDAD_CHAT, ImagenAdjunta, Mensaje
from app.shared.domain.errors import NoDisponible, NoEncontrado

from .request import MensajeEntrante, MensajeResponse

MSG_EXPIRADO = "Este chat expiró"  # RF-CHT-25


def url_imagen(chat_id: str, mensaje_id: str) -> str:
    return f"/api/chats/{chat_id}/mensajes/{mensaje_id}/imagen"


class EnviarMensajeHandler:
    def __init__(self, chats: IChatRepository, imagenes: ImageStorage, clock: IClock) -> None:
        self._chats = chats
        self._imagenes = imagenes
        self._clock = clock

    async def handle(self, estudiante_id: str, nickname: str, chat_id: str, body: MensajeEntrante) -> MensajeResponse:
        ahora = self._clock.ahora()
        chat = await self._chats.buscar_por_id(chat_id)
        if chat is None or estudiante_id not in chat.participantes:
            raise NoEncontrado("El chat no existe", codigo="chat_inexistente")  # RNF-SEG-04
        if not chat.activo(ahora):
            raise NoDisponible(MSG_EXPIRADO, codigo="chat_expirado")  # RF-CHT-15

        imagen = None
        if body.imagen is not None:
            referencia = await self._imagenes.guardar(body.imagen, body.imagen_mime)
            imagen = ImagenAdjunta(referencia, body.imagen_mime, len(body.imagen))
        mensaje = Mensaje(id="", chat_id=chat.id, emisor_id=estudiante_id, nickname_emisor=nickname,
                          fecha_envio=ahora, texto=body.texto, imagen=imagen)
        expiracion = ahora + INACTIVIDAD_CHAT
        try:
            mensaje_id = await self._chats.agregar_mensaje(mensaje, expiracion)
        except Exception:
            if imagen is not None:
                await self._imagenes.eliminar(imagen.referencia)
            raise
        if mensaje_id is None:
            if imagen is not None:
                await self._imagenes.eliminar(imagen.referencia)
            raise NoDisponible(MSG_EXPIRADO, codigo="chat_expirado")
        return MensajeResponse(id=mensaje_id, es_propio=True, nickname_emisor=nickname, texto=body.texto,
                               imagen_url=url_imagen(chat.id, mensaje_id) if imagen else None,
                               fecha_envio=ahora, hora=hora_hhmm(ahora), fecha_expiracion_chat=expiracion)
