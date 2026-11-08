"""CU-01 — Registrar cuenta. Controlador MVC (APIRouter), sin lógica de negocio."""
from fastapi import APIRouter, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.config.provider import get_config, variable
from app.shared.db.mongo import get_database
from app.shared.domain.entities import ClaveParametro
from app.shared.email.sender import get_email_sender, url_base
from app.shared.security.hashing import BcryptPasswordHasher, SecureTokenService
from app.shared.security.session import SesionActual, get_sesion_opcional
from app.shared.web.plantillas import redirigir, render

from .handler import RegistrarCuentaHandler
from .repository import MongoRegistrarCuentaRepository
from .request import MensajeResponse, RegistrarCuentaRequest

router = APIRouter(tags=["M01 Acceso"])


def get_handler(db: AsyncIOMotorDatabase = Depends(get_database)) -> RegistrarCuentaHandler:
    return RegistrarCuentaHandler(
        cuentas=MongoRegistrarCuentaRepository(db),
        hasher=BcryptPasswordHasher(),
        tokens=SecureTokenService(),
        correo=get_email_sender(),
        config=get_config(),
        clock=get_clock(),
        url_base=url_base(),
        version_terminos=variable("TERMINOS_VERSION", "pendiente") or "pendiente",
    )


@router.post("/api/cuentas", response_model=MensajeResponse, status_code=201)
async def registrar_cuenta(
    body: RegistrarCuentaRequest,
    handler: RegistrarCuentaHandler = Depends(get_handler),
) -> MensajeResponse:
    return await handler.handle(body)


def _dominio() -> str:
    try:
        return get_config().texto(ClaveParametro.DOMINIO_INSTITUCIONAL)
    except RuntimeError:
        return ""


@router.get("/registro", include_in_schema=False)
async def pagina_registro(request: Request, sesion: SesionActual | None = Depends(get_sesion_opcional)):
    if sesion is not None:
        return redirigir("/feed")
    return render(request, "m01_acceso/registro.html", sesion, dominio=_dominio())
