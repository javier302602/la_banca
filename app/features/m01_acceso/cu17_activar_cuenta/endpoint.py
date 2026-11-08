"""CU-17 — Activar la cuenta. Controlador MVC (APIRouter), sin lógica de negocio.

La activación se confirma con POST desde la página /activar (no con el GET del enlace), para que los
escáneres de correo que abren enlaces automáticamente no consuman el token de un solo uso.
"""
from fastapi import APIRouter, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.email.sender import get_email_sender, url_base
from app.shared.security.hashing import SecureTokenService
from app.shared.security.session import SesionActual, get_sesion_opcional
from app.shared.web.plantillas import render

from .handler import ActivarCuentaHandler
from .repository import MongoActivarCuentaRepository
from .request import ActivarCuentaRequest, MensajeResponse, ReenviarActivacionRequest

router = APIRouter(tags=["M01 Acceso"])


def get_handler(db: AsyncIOMotorDatabase = Depends(get_database)) -> ActivarCuentaHandler:
    return ActivarCuentaHandler(
        cuentas=MongoActivarCuentaRepository(db),
        tokens=SecureTokenService(),
        correo=get_email_sender(),
        clock=get_clock(),
        url_base=url_base(),
    )


@router.post("/api/cuentas/activar", response_model=MensajeResponse, status_code=200)
async def activar_cuenta(
    body: ActivarCuentaRequest,
    handler: ActivarCuentaHandler = Depends(get_handler),
) -> MensajeResponse:
    return await handler.handle(body)


@router.post("/api/cuentas/activacion/reenviar", response_model=MensajeResponse, status_code=202)
async def reenviar_activacion(
    body: ReenviarActivacionRequest,
    handler: ActivarCuentaHandler = Depends(get_handler),
) -> MensajeResponse:
    return await handler.reenviar(body)


@router.get("/activar", include_in_schema=False)
async def pagina_activar(request: Request, sesion: SesionActual | None = Depends(get_sesion_opcional)):
    return render(request, "m01_acceso/activar_cuenta.html", sesion, token=request.query_params.get("token"))
