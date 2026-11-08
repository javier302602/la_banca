"""CU-17 — Activar la cuenta. Controlador MVC (APIRouter), sin lógica de negocio."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.email.sender import get_email_sender
from app.shared.security.hashing import SecureTokenService

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
    )


@router.get("/cuentas/activar", response_model=MensajeResponse, status_code=200)
async def activar_cuenta(
    body: Annotated[ActivarCuentaRequest, Query()],
    handler: ActivarCuentaHandler = Depends(get_handler),
) -> MensajeResponse:
    """Delegar en el handler."""
    raise NotImplementedError


@router.post("/cuentas/activacion/reenviar", response_model=MensajeResponse, status_code=202)
async def reenviar_activacion(
    body: ReenviarActivacionRequest,
    handler: ActivarCuentaHandler = Depends(get_handler),
) -> MensajeResponse:
    """Delegar en el handler."""
    raise NotImplementedError
