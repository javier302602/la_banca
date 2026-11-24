"""CU-21 — Reaccionar a una publicación. Controlador (APIRouter), sin lógica de negocio."""
from fastapi import APIRouter, Depends
from pymongo.asynchronous.database import AsyncDatabase

from app.features.m03_feed.cu09_ver_detalle_publicacion.repository import MongoVerDetallePublicacionRepository
from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.security.session import SesionActual, get_sesion_actual

from .handler import ReaccionarPublicacionHandler
from .repository import MongoReaccionesRepository
from .request import ReaccionarRequest, ReaccionesResponse

router = APIRouter(tags=["M02 Publicaciones"])


def get_handler(db: AsyncDatabase = Depends(get_database)) -> ReaccionarPublicacionHandler:
    return ReaccionarPublicacionHandler(
        publicaciones=MongoVerDetallePublicacionRepository(db),
        reacciones=MongoReaccionesRepository(db),
        clock=get_clock(),
    )


@router.put("/api/publicaciones/{publicacion_id}/reaccion", response_model=ReaccionesResponse, status_code=200)
async def reaccionar(
    publicacion_id: str,
    body: ReaccionarRequest,
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: ReaccionarPublicacionHandler = Depends(get_handler),
) -> ReaccionesResponse:
    return await handler.handle(sesion.estudiante_id, publicacion_id, body)
