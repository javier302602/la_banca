"""CU-11 — Enviar mensaje en un chat. Controlador MVC (APIRouter), sin lógica de negocio."""
from fastapi import APIRouter, Depends, File, Form, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.security.session import SesionActual, get_sesion_actual
from app.shared.storage.image_storage import get_image_storage, leer_imagen_subida

from .handler import EnviarMensajeHandler
from .repository import MongoEnviarMensajeRepository
from .request import MensajeEntrante, MensajeResponse

router = APIRouter(tags=["M04 Chat"])


def get_handler(db: AsyncIOMotorDatabase = Depends(get_database)) -> EnviarMensajeHandler:
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
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: EnviarMensajeHandler = Depends(get_handler),
) -> MensajeResponse:
    body = MensajeEntrante(texto=texto, imagen=await leer_imagen_subida(imagen))
    return await handler.handle(sesion.estudiante_id, sesion.nickname, chat_id, body)
