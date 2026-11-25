"""CU-26 — Moderar un reporte. Controlador (APIRouter), sin lógica de negocio. Solo administradores."""
from fastapi import APIRouter, Depends
from pymongo.asynchronous.database import AsyncDatabase

from app.features.m09_admin.cu25_panel_reportes.handler import respuesta
from app.features.m09_admin.cu25_panel_reportes.repository import MongoAdminRepository
from app.features.m09_admin.cu25_panel_reportes.request import ReporteAdminResponse
from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.email.sender import get_email_sender
from app.shared.security.session import SesionActual, get_sesion_admin
from app.shared.storage.image_storage import get_image_storage

from .handler import ModerarReporteHandler
from .request import AccionRequest

router = APIRouter(tags=["M09 Administración"])


@router.post("/api/admin/reportes/{origen}/{reporte_id}/acciones", response_model=ReporteAdminResponse, status_code=200)
async def moderar_reporte(origen: str, reporte_id: str, body: AccionRequest,
                          sesion: SesionActual = Depends(get_sesion_admin),
                          db: AsyncDatabase = Depends(get_database)) -> ReporteAdminResponse:
    admin = MongoAdminRepository(db)
    handler = ModerarReporteHandler(admin, get_image_storage(), get_email_sender(), get_clock())
    reporte = await handler.handle(sesion.estudiante_id, origen, reporte_id, body)
    perfiles = await admin.perfiles({reporte.reportante_id, reporte.reportado_id} - {None})
    return respuesta(reporte, perfiles)
