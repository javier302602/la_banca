"""CU-24 — Reportar videollamada. Controlador (APIRouter), sin lógica de negocio."""
from fastapi import APIRouter, Depends
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.email.sender import get_email_sender
from app.shared.security.session import SesionActual, get_sesion_actual

from .handler import ReportarVideollamadaHandler
from .repository import MongoReportarVideollamadaRepository
from .request import ReportarVideollamadaRequest, ReporteVideollamadaResponse

router = APIRouter(tags=["M08 Videollamada"])


def get_handler(db: AsyncDatabase = Depends(get_database)) -> ReportarVideollamadaHandler:
    return ReportarVideollamadaHandler(MongoReportarVideollamadaRepository(db), get_clock(), avisos=get_email_sender())


@router.post("/api/videollamada/reportes", response_model=ReporteVideollamadaResponse, status_code=201)
async def reportar_videollamada(
    body: ReportarVideollamadaRequest,
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: ReportarVideollamadaHandler = Depends(get_handler),
) -> ReporteVideollamadaResponse:
    return await handler.handle(sesion.estudiante_id, body)
