"""CU-03 — Cerrar sesión manualmente. Controlador MVC (APIRouter), sin lógica de negocio."""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.security.session import SesionActual, get_sesion_actual

from .handler import CerrarSesionHandler
from .repository import MongoCerrarSesionRepository

router = APIRouter(tags=["M01 Acceso"])


def get_handler(db: AsyncIOMotorDatabase = Depends(get_database)) -> CerrarSesionHandler:
    return CerrarSesionHandler(
        cuentas=MongoCerrarSesionRepository(db),
        clock=get_clock(),
    )


@router.post("/sesiones/cerrar", status_code=204)
async def cerrar_sesion(
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: CerrarSesionHandler = Depends(get_handler),
) -> None:
    """Delegar en el handler."""
    raise NotImplementedError
