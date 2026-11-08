"""CU-18 — Recuperar la contraseña. Controlador MVC (APIRouter), sin lógica de negocio."""
from fastapi import APIRouter, Depends, Request
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.email.sender import get_email_sender, url_base
from app.shared.security.hashing import BcryptPasswordHasher, SecureTokenService
from app.shared.security.session import SesionActual, get_sesion_opcional
from app.shared.web.plantillas import render

from .handler import RecuperarContrasenaHandler
from .repository import MongoRecuperarContrasenaRepository
from .request import MensajeResponse, RestablecerContrasenaRequest, SolicitarRecuperacionRequest

router = APIRouter(tags=["M01 Acceso"])


def get_handler(db: AsyncDatabase = Depends(get_database)) -> RecuperarContrasenaHandler:
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


@router.get("/recuperar", include_in_schema=False)
async def pagina_recuperar(request: Request, sesion: SesionActual | None = Depends(get_sesion_opcional)):
    return render(request, "m01_acceso/recuperar_contrasena.html", sesion)


@router.get("/restablecer", include_in_schema=False)
async def pagina_restablecer(request: Request, sesion: SesionActual | None = Depends(get_sesion_opcional)):
    return render(request, "m01_acceso/restablecer_contrasena.html", sesion, token=request.query_params.get("token"))
