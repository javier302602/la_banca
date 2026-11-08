"""CU-02 — Iniciar sesión. Controlador MVC (APIRouter), sin lógica de negocio."""
from fastapi import APIRouter, Depends, Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.config.provider import get_config
from app.shared.db.mongo import get_database
from app.shared.security.hashing import BcryptPasswordHasher, SecureTokenService
from app.shared.security.session import escribir_cookie_sesion

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


@router.post("/api/sesiones", response_model=SesionResponse, status_code=200)
async def iniciar_sesion(
    body: IniciarSesionRequest,
    response: Response,
    handler: IniciarSesionHandler = Depends(get_handler),
) -> SesionResponse:
    resultado = await handler.handle(body)
    escribir_cookie_sesion(response, resultado.token)
    return resultado.respuesta
