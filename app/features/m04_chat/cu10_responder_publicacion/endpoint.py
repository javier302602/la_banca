"""CU-10 — Responder a una publicación. Controlador MVC (APIRouter), sin lógica de negocio."""
from fastapi import APIRouter, Depends, File, Form, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.security.session import SesionActual, get_sesion_actual
from app.shared.storage.image_storage import get_image_storage, leer_imagen_subida

from .handler import ResponderPublicacionHandler
from .repository import MongoPublicacionLecturaRepository, MongoResponderPublicacionRepository
from .request import ChatCreadoResponse, MensajeEntrante

router = APIRouter(tags=["M04 Chat"])


def get_handler(db: AsyncIOMotorDatabase = Depends(get_database)) -> ResponderPublicacionHandler:
    return ResponderPublicacionHandler(
        publicaciones=MongoPublicacionLecturaRepository(db),
        chats=MongoResponderPublicacionRepository(db),
        imagenes=get_image_storage(),
        clock=get_clock(),
    )


@router.post("/api/publicaciones/{publicacion_id}/respuestas", response_model=ChatCreadoResponse, status_code=201)
async def responder_publicacion(
    publicacion_id: str,
    texto: str | None = Form(default=None),
    imagen: UploadFile | None = File(default=None),
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: ResponderPublicacionHandler = Depends(get_handler),
) -> ChatCreadoResponse:
    body = MensajeEntrante(texto=texto, imagen=await leer_imagen_subida(imagen))
    return await handler.handle(sesion.estudiante_id, sesion.nickname, publicacion_id, body)
