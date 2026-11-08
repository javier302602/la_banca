"""CU-10 — Responder a una publicación. Caso de uso (handler).

RF: RF-CHT-01–10, RF-CHT-23, RF-CHT-24, RF-CHT-26
Crea un único chat 1 a 1 por (publicación, usuario) junto con su primer mensaje, de forma atómica
(RNF-FIA-03). El conteo de inactividad (24 h, RN-20) empieza con ese mensaje (RF-CHT-03).
- No se responde a una publicación propia (RF-CHT-04) ni a una cerrada o vencida (RF-CHT-06).
- Con un chat activo sobre la publicación se rechaza y se ofrece abrirlo (RF-CHT-05, RF-CHT-23).
- Si el chat anterior expiró se crea uno nuevo, sin los mensajes del anterior (RF-CHT-24).
"""
from app.shared.domain.contracts import IChatRepository, IClock, ImageStorage, IPublicationRepository
from app.shared.domain.entities import INACTIVIDAD_CHAT, Chat, ImagenAdjunta, Mensaje
from app.shared.domain.errors import Conflicto, NoDisponible, Prohibido

from .request import ChatCreadoResponse, MensajeEntrante

MSG_NO_DISPONIBLE = "Esta publicación ya no está disponible"          # RF-CHT-06
MSG_PROPIA = "No puedes responder a tu propia publicación"            # RF-CHT-04
MSG_CHAT_EXISTENTE = "Ya tienes un chat activo sobre esta publicación"  # RF-CHT-05


class ResponderPublicacionHandler:
    def __init__(self, publicaciones: IPublicationRepository, chats: IChatRepository, imagenes: ImageStorage,
                 clock: IClock) -> None:
        self._publicaciones = publicaciones
        self._chats = chats
        self._imagenes = imagenes
        self._clock = clock

    async def handle(self, estudiante_id: str, nickname: str, publicacion_id: str,
                     body: MensajeEntrante) -> ChatCreadoResponse:
        ahora = self._clock.ahora()
        publicacion = await self._publicaciones.buscar_por_id(publicacion_id)
        if publicacion is None or not publicacion.activa(ahora):
            raise NoDisponible(MSG_NO_DISPONIBLE, codigo="publicacion_no_disponible")
        if publicacion.autor_id == estudiante_id:
            raise Prohibido(MSG_PROPIA, codigo="publicacion_propia")

        anterior = await self._chats.buscar_por_usuario_y_publicacion(estudiante_id, publicacion.id)
        if anterior is not None:
            if anterior.activo(ahora):
                raise Conflicto(MSG_CHAT_EXISTENTE, codigo="chat_existente", chat_id=anterior.id)
            for referencia in await self._chats.eliminar_chat(anterior.id):  # RF-CHT-24
                await self._imagenes.eliminar(referencia)

        imagen = None
        if body.imagen is not None:
            referencia = await self._imagenes.guardar(body.imagen, body.imagen_mime)
            imagen = ImagenAdjunta(referencia, body.imagen_mime, len(body.imagen), self._imagenes.bucket)
        chat = Chat(
            id="", publicacion_id=publicacion.id, autor_id=publicacion.autor_id, respondedor_id=estudiante_id,
            fecha_inicio=ahora, ultima_actividad=ahora, fecha_expiracion=ahora + INACTIVIDAD_CHAT,
            tipo_publicacion=publicacion.tipo, titulo_publicacion=publicacion.titulo,
            nickname_autor=publicacion.nickname_autor, nickname_respondedor=nickname,
            ultima_lectura={estudiante_id: ahora},
        )
        mensaje = Mensaje(id="", chat_id="", emisor_id=estudiante_id, nickname_emisor=nickname,
                          fecha_envio=ahora, texto=body.texto, imagen=imagen)
        try:
            chat_id = await self._chats.crear_con_primer_mensaje(chat, mensaje)
        except Exception as error:
            if imagen is not None:  # sin registros a medias (RNF-FIA-03)
                await self._imagenes.eliminar(imagen.referencia)
            if isinstance(error, Conflicto):
                existente = await self._chats.buscar_por_usuario_y_publicacion(estudiante_id, publicacion.id)
                raise Conflicto(MSG_CHAT_EXISTENTE, codigo="chat_existente",
                                chat_id=existente.id if existente else None) from None
            raise
        return ChatCreadoResponse(chat_id=chat_id, nickname_autor=publicacion.nickname_autor)
