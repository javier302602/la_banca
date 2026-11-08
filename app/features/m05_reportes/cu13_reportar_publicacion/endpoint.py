"""CU-13 — Reportar una publicación. Controlador MVC (APIRouter), sin lógica de negocio."""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.config.provider import get_config
from app.shared.db.mongo import get_database
from app.shared.security.session import SesionActual, get_sesion_actual

from .handler import ReportarPublicacionHandler
from .repository import MongoPublicacionLecturaRepository, MongoReportarPublicacionRepository
from .request import ReporteRequest, ReporteResponse

router = APIRouter(tags=["M05 Reportes"])


def get_handler(db: AsyncIOMotorDatabase = Depends(get_database)) -> ReportarPublicacionHandler:
    return ReportarPublicacionHandler(
        publicaciones=MongoPublicacionLecturaRepository(db),
        reportes=MongoReportarPublicacionRepository(db),
        config=get_config(),
        clock=get_clock(),
    )


@router.post("/publicaciones/{publicacion_id}/reportes", response_model=ReporteResponse, status_code=201)
async def reportar_publicacion(
    publicacion_id: str,
    body: ReporteRequest,
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: ReportarPublicacionHandler = Depends(get_handler),
) -> ReporteResponse:
    """Delegar en el handler."""
    raise NotImplementedError
