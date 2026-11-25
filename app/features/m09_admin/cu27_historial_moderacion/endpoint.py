"""CU-27 — Historial de moderación. Controlador (APIRouter). Solo administradores."""
from fastapi import APIRouter, Depends
from pymongo.asynchronous.database import AsyncDatabase

from app.features.m09_admin.cu25_panel_reportes.repository import MongoAdminRepository
from app.shared.db.mongo import get_database
from app.shared.security.session import SesionActual, get_sesion_admin

from .handler import HistorialHandler
from .request import HistorialResponse

router = APIRouter(tags=["M09 Administración"])


@router.get("/api/admin/historial", response_model=HistorialResponse, status_code=200)
async def ver_historial(sesion: SesionActual = Depends(get_sesion_admin),
                        db: AsyncDatabase = Depends(get_database)) -> HistorialResponse:
    return await HistorialHandler(MongoAdminRepository(db)).handle()
