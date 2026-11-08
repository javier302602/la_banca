"""CU-05 — Crear publicación. Controlador MVC (APIRouter), sin lógica de negocio."""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.config.provider import get_config
from app.shared.db.mongo import get_database
from app.shared.security.session import SesionActual, get_sesion_actual

from .handler import CrearPublicacionHandler
from .repository import MongoCrearPublicacionRepository
from .request import CrearPublicacionRequest, PublicacionResponse

router = APIRouter(tags=["M02 Publicaciones"])


def get_handler(db: AsyncIOMotorDatabase = Depends(get_database)) -> CrearPublicacionHandler:
    return CrearPublicacionHandler(
        publicaciones=MongoCrearPublicacionRepository(db),
        config=get_config(),
        clock=get_clock(),
    )


@router.post("/publicaciones", response_model=PublicacionResponse, status_code=201)
async def crear_publicacion(
    body: CrearPublicacionRequest,
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: CrearPublicacionHandler = Depends(get_handler),
) -> PublicacionResponse:
    """Delegar en el handler."""
    raise NotImplementedError
