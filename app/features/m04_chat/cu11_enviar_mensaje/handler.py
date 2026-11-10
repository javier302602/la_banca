"""CU-11 — Enviar mensaje en un chat. Caso de uso (handler).

RF: RF-CHT-08–12, RF-CHT-15, RF-CHT-20, RF-CHT-22, RF-CHT-25, RF-CHT-26
Solo los participantes de un chat vigente pueden enviar. Cada mensaje reinicia el conteo de
inactividad: nueva expiración = hora del mensaje + 24 h (RF-CHT-12). El chat se verifica de forma
atómica al registrar el mensaje, por si expira entre la lectura y la escritura.
"""
from app.shared.clock import hora_hhmm
from app.shared.domain.contracts import IChatRepository, IClock, ImageStorage
from app.shared.domain.documentos import validar_documento
from app.shared.domain.entities import INACTIVIDAD_CHAT, DocumentoAdjunto, ImagenAdjunta, Mensaje
from app.shared.domain.errors import ErrorValidacion, NoDisponible, NoEncontrado

from .request import DocumentoResponse, MensajeEntrante, MensajeResponse

PREFIJO_DOCUMENTOS = "documentos"

MSG_EXPIRADO = "Este chat expiró"  # RF-CHT-25


def url_imagen(chat_id: str, mensaje_id: str) -> str:
    return f"/api/chats/{chat_id}/mensajes/{mensaje_id}/imagen"


def url_documento(chat_id: str, mensaje_id: str) -> str:
    return f"/api/chats/{chat_id}/mensajes/{mensaje_id}/documento"


def url_sticker(sticker: str) -> str:
    return f"/static/stickers/{sticker}.svg"


def documento_response(chat_id: str, mensaje_id: str, d: DocumentoAdjunto | None) -> DocumentoResponse | None:
    if d is None:
        return None
    return DocumentoResponse(nombre=d.nombre, tipo=d.tipo, tamano_bytes=d.tamano_bytes,
                             url=url_documento(chat_id, mensaje_id))


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

        imagen = documento = None
        if body.documento is not None:
            try:
                validado = validar_documento(body.documento, body.documento_nombre)
            except ValueError as e:
                raise ErrorValidacion(str(e), codigo="documento_invalido", campo="documento") from None
            referencia = await self._imagenes.guardar_procesado(body.documento, validado.mime_type, PREFIJO_DOCUMENTOS)
            documento = DocumentoAdjunto(referencia, validado.mime_type, len(body.documento), validado.nombre,
                                         validado.tipo, self._imagenes.bucket)
        if body.imagen is not None:
            referencia = await self._imagenes.guardar(body.imagen, body.imagen_mime)
            imagen = ImagenAdjunta(referencia, body.imagen_mime, len(body.imagen), self._imagenes.bucket)
        mensaje = Mensaje(id="", chat_id=chat.id, emisor_id=estudiante_id, nickname_emisor=nickname,
                          fecha_envio=ahora, texto=body.texto, imagen=imagen, sticker=body.sticker, documento=documento)
        expiracion = ahora + INACTIVIDAD_CHAT
        try:
            mensaje_id = await self._chats.agregar_mensaje(mensaje, expiracion)
        except Exception:
            await self._borrar(mensaje)
            raise
        if mensaje_id is None:
            await self._borrar(mensaje)
            raise NoDisponible(MSG_EXPIRADO, codigo="chat_expirado")
        return MensajeResponse(id=mensaje_id, es_propio=True, nickname_emisor=nickname, texto=body.texto,
                               imagen_url=url_imagen(chat.id, mensaje_id) if imagen else None,
                               sticker=body.sticker, sticker_url=url_sticker(body.sticker) if body.sticker else None,
                               documento=documento_response(chat.id, mensaje_id, documento),
                               fecha_envio=ahora, hora=hora_hhmm(ahora), fecha_expiracion_chat=expiracion)

    async def _borrar(self, mensaje: Mensaje) -> None:
        for referencia in mensaje.archivos:
            await self._imagenes.eliminar(referencia)
