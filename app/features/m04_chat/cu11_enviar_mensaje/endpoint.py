"""CU-11 — Enviar mensaje en un chat. Controlador MVC (APIRouter), sin lógica de negocio."""
from fastapi import APIRouter, Depends, File, Form, UploadFile
from pymongo.asynchronous.database import AsyncDatabase

from app.features.m09_admin.cu28_filtro_automatico.handler import FiltroAutomatico
from app.features.m09_admin.cu28_filtro_automatico.repository import MongoFiltroRepository
from app.shared.clock import get_clock
from app.shared.config.provider import get_config
from app.shared.config.provider import variable
from app.shared.db.mongo import get_database
from app.shared.domain.documentos import TAMANO_MAX_DOCUMENTO
from app.shared.domain.errors import ErrorValidacion
from app.shared.domain.reglas import MSG_UN_CONTENIDO
from app.shared.email.sender import get_email_sender
from app.shared.security.session import SesionActual, get_sesion_actual
from app.shared.storage.image_storage import get_image_storage, leer_imagen_subida

from .handler import EnviarMensajeHandler
from .repository import MongoEnviarMensajeRepository
from .request import MensajeEntrante, MensajeResponse

router = APIRouter(tags=["M04 Chat"])


def tamano_max_audio() -> int:
    """Tamaño máximo de un audio en bytes, desde AUDIO_MAX_MB (.env; 20 MB por omisión)."""
    return int(variable("AUDIO_MAX_MB", "20") or "20") * 1024 * 1024


def get_handler(db: AsyncDatabase = Depends(get_database)) -> EnviarMensajeHandler:
    return EnviarMensajeHandler(
        chats=MongoEnviarMensajeRepository(db),
        imagenes=get_image_storage(),
        clock=get_clock(),
        tamano_max_audio=tamano_max_audio(),
        filtro=FiltroAutomatico(MongoFiltroRepository(db), get_config(), get_clock(), get_email_sender()),
    )


@router.post("/api/chats/{chat_id}/mensajes", response_model=MensajeResponse, status_code=201)
async def enviar_mensaje(
    chat_id: str,
    texto: str | None = Form(default=None),
    imagen: UploadFile | None = File(default=None),
    sticker: str | None = Form(default=None, max_length=20),
    documento: UploadFile | None = File(default=None),
    audio: UploadFile | None = File(default=None),
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: EnviarMensajeHandler = Depends(get_handler),
) -> MensajeResponse:
    contenido_documento = await leer_imagen_subida(documento, TAMANO_MAX_DOCUMENTO)
    contenido_audio = await leer_imagen_subida(audio, tamano_max_audio())
    if contenido_documento is not None and contenido_audio is not None:
        raise ErrorValidacion(MSG_UN_CONTENIDO, codigo="validacion", campo="audio")
    # El audio viaja como un documento más del mensaje (ver app/shared/domain/audios.py)
    adjunto = audio if contenido_audio is not None else documento
    body = MensajeEntrante(texto=texto, imagen=await leer_imagen_subida(imagen), sticker=sticker,
                           documento=contenido_audio if contenido_audio is not None else contenido_documento,
                           documento_nombre=adjunto.filename if adjunto else None,
                           es_audio=contenido_audio is not None)
    return await handler.handle(sesion.estudiante_id, sesion.nickname, chat_id, body)
