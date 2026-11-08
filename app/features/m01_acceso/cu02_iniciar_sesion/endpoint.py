"""CU-02 — Iniciar sesión. Controlador MVC (APIRouter), sin lógica de negocio."""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.config.provider import get_config
from app.shared.db.mongo import get_database
from app.shared.security.hashing import BcryptPasswordHasher
from app.shared.security.hashing import SecureTokenService

from .handler import IniciarSesionHandler
from .repository import MongoIniciarSesionRepository
from .request import IniciarSesionRequest, SesionResponse

router = APIRouter(tags=["M01 Acceso"])


def get_handler(db: AsyncIOMotorDatabase = Depends(get_database)) -> IniciarSesionHandler:
    return IniciarSesionHandler(
        cuentas=MongoIniciarSesionRepository(db),
        hasher=BcryptPasswordHasher(),
        tokens=SecureTokenService(),
        config=get_config(),
        clock=get_clock(),
    )


@router.post("/sesiones", response_model=SesionResponse, status_code=200)
async def iniciar_sesion(
    body: IniciarSesionRequest,
    handler: IniciarSesionHandler = Depends(get_handler),
) -> SesionResponse:
    """Delegar en el handler."""
    raise NotImplementedError
