"""CU-03 — Cerrar sesión manualmente. Controlador MVC (APIRouter), sin lógica de negocio."""
from fastapi import APIRouter, Depends, Request, Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.security.hashing import SecureTokenService
from app.shared.security.session import COOKIE_SESION, borrar_cookie_sesion

from .handler import CerrarSesionHandler
from .repository import MongoCerrarSesionRepository

router = APIRouter(tags=["M01 Acceso"])


def get_handler(db: AsyncIOMotorDatabase = Depends(get_database)) -> CerrarSesionHandler:
    return CerrarSesionHandler(
        cuentas=MongoCerrarSesionRepository(db),
        tokens=SecureTokenService(),
        clock=get_clock(),
    )


@router.post("/api/sesiones/cerrar", status_code=204)
async def cerrar_sesion(
    request: Request,
    response: Response,
    handler: CerrarSesionHandler = Depends(get_handler),
) -> None:
    await handler.handle(request.cookies.get(COOKIE_SESION))
    borrar_cookie_sesion(response)
