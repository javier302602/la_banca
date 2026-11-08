"""CU-13 — Reportar una publicación. Controlador MVC (APIRouter), sin lógica de negocio."""
from fastapi import APIRouter, Depends, Request
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.clock import get_clock
from app.shared.config.provider import get_config
from app.shared.db.mongo import get_database
from app.shared.domain.entities import MOTIVOS_REPORTE
from app.shared.security.session import SesionActual, get_sesion_actual, get_sesion_opcional
from app.shared.web.plantillas import redirigir_a_login, render

from .handler import ReportarPublicacionHandler
from .repository import MongoPublicacionLecturaRepository, MongoReportarPublicacionRepository
from .request import ReporteRequest, ReporteResponse

router = APIRouter(tags=["M05 Reportes"])


def get_handler(db: AsyncDatabase = Depends(get_database)) -> ReportarPublicacionHandler:
    return ReportarPublicacionHandler(
        publicaciones=MongoPublicacionLecturaRepository(db),
        reportes=MongoReportarPublicacionRepository(db),
        config=get_config(),
        clock=get_clock(),
    )


@router.post("/api/publicaciones/{publicacion_id}/reportes", response_model=ReporteResponse, status_code=201)
async def reportar_publicacion(
    publicacion_id: str,
    body: ReporteRequest,
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: ReportarPublicacionHandler = Depends(get_handler),
) -> ReporteResponse:
    return await handler.handle(sesion.estudiante_id, publicacion_id, body)


@router.get("/publicaciones/{publicacion_id}/reportar", include_in_schema=False)
async def pagina_reportar(request: Request, publicacion_id: str, sesion: SesionActual | None = Depends(get_sesion_opcional)):
    if sesion is None:
        return redirigir_a_login(request)
    return render(request, "m05_reportes/reportar.html", sesion, objeto="publicación", motivos=list(MOTIVOS_REPORTE.values()), volver=f"/publicaciones/{publicacion_id}", endpoint_api=f"/api/publicaciones/{publicacion_id}/reportes")
