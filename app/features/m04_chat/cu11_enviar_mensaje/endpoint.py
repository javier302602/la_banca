"""CU-11 — Enviar mensaje en un chat. Controlador MVC (APIRouter), sin lógica de negocio."""
from fastapi import APIRouter, Depends, File, Form, UploadFile
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.domain.documentos import TAMANO_MAX_DOCUMENTO
from app.shared.security.session import SesionActual, get_sesion_actual
from app.shared.storage.image_storage import get_image_storage, leer_imagen_subida

from .handler import EnviarMensajeHandler
from .repository import MongoEnviarMensajeRepository
from .request import MensajeEntrante, MensajeResponse

router = APIRouter(tags=["M04 Chat"])


def get_handler(db: AsyncDatabase = Depends(get_database)) -> EnviarMensajeHandler:
    return EnviarMensajeHandler(
        chats=MongoEnviarMensajeRepository(db),
        imagenes=get_image_storage(),
        clock=get_clock(),
    )


@router.post("/api/chats/{chat_id}/mensajes", response_model=MensajeResponse, status_code=201)
async def enviar_mensaje(
    chat_id: str,
    texto: str | None = Form(default=None),
    imagen: UploadFile | None = File(default=None),
    sticker: str | None = Form(default=None, max_length=20),
    documento: UploadFile | None = File(default=None),
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: EnviarMensajeHandler = Depends(get_handler),
) -> MensajeResponse:
    body = MensajeEntrante(texto=texto, imagen=await leer_imagen_subida(imagen), sticker=sticker,
                           documento=await leer_imagen_subida(documento, TAMANO_MAX_DOCUMENTO),
                           documento_nombre=documento.filename if documento else None)
    return await handler.handle(sesion.estudiante_id, sesion.nickname, chat_id, body)
