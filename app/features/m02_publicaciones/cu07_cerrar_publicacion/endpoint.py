"""CU-07 — Cerrar publicación manualmente. Controlador MVC (APIRouter), sin lógica de negocio."""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.security.session import SesionActual, get_sesion_actual

from .handler import CerrarPublicacionHandler
from .repository import MongoCerrarPublicacionRepository

router = APIRouter(tags=["M02 Publicaciones"])


def get_handler(db: AsyncIOMotorDatabase = Depends(get_database)) -> CerrarPublicacionHandler:
    return CerrarPublicacionHandler(
        publicaciones=MongoCerrarPublicacionRepository(db),
        clock=get_clock(),
    )


@router.post("/publicaciones/{publicacion_id}/cerrar", status_code=204)
async def cerrar_publicacion(
    publicacion_id: str,
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: CerrarPublicacionHandler = Depends(get_handler),
) -> None:
    """Delegar en el handler."""
    raise NotImplementedError
