"""CU-18 — Recuperar la contraseña. Controlador MVC (APIRouter), sin lógica de negocio."""
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.email.sender import get_email_sender, url_base
from app.shared.security.hashing import BcryptPasswordHasher, SecureTokenService

from .handler import RecuperarContrasenaHandler
from .repository import MongoRecuperarContrasenaRepository
from .request import MensajeResponse, RestablecerContrasenaRequest, SolicitarRecuperacionRequest

router = APIRouter(tags=["M01 Acceso"])


def get_handler(db: AsyncIOMotorDatabase = Depends(get_database)) -> RecuperarContrasenaHandler:
    return RecuperarContrasenaHandler(
        cuentas=MongoRecuperarContrasenaRepository(db),
        tokens=SecureTokenService(),
        hasher=BcryptPasswordHasher(),
        correo=get_email_sender(),
        clock=get_clock(),
        url_base=url_base(),
    )


@router.post("/api/contrasena/recuperar", response_model=MensajeResponse, status_code=202)
async def solicitar_recuperacion(
    body: SolicitarRecuperacionRequest,
    handler: RecuperarContrasenaHandler = Depends(get_handler),
) -> MensajeResponse:
    return await handler.handle(body)


@router.post("/api/contrasena/restablecer", response_model=MensajeResponse, status_code=200)
async def restablecer_contrasena(
    body: RestablecerContrasenaRequest,
    handler: RecuperarContrasenaHandler = Depends(get_handler),
) -> MensajeResponse:
    return await handler.restablecer(body)
