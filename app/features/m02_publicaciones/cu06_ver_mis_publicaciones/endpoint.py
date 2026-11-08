"""CU-06 — Ver mis publicaciones activas. Controlador MVC (APIRouter), sin lógica de negocio."""
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.security.session import SesionActual, get_sesion_actual

from .handler import VerMisPublicacionesHandler
from .repository import MongoVerMisPublicacionesRepository
from .request import MisPublicacionesResponse

router = APIRouter(tags=["M02 Publicaciones"])


def get_handler(db: AsyncIOMotorDatabase = Depends(get_database)) -> VerMisPublicacionesHandler:
    return VerMisPublicacionesHandler(publicaciones=MongoVerMisPublicacionesRepository(db), clock=get_clock())


@router.get("/api/publicaciones/mias", response_model=MisPublicacionesResponse, status_code=200)
async def ver_mis_publicaciones(
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: VerMisPublicacionesHandler = Depends(get_handler),
) -> MisPublicacionesResponse:
    return await handler.handle(sesion.estudiante_id)
