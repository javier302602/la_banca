"""CU-16 — Consultar términos de uso y política de privacidad. Controlador MVC (APIRouter)."""
from fastapi import APIRouter, Depends

from app.shared.config.provider import variable

from .handler import ConsultarTerminosHandler
from .repository import leer_terminos
from .request import TerminosResponse

router = APIRouter(tags=["M01 Acceso"])


def get_handler() -> ConsultarTerminosHandler:
    return ConsultarTerminosHandler(variable("TERMINOS_VERSION"), variable("TERMINOS_FECHA"), leer_terminos)


@router.get("/api/terminos", response_model=TerminosResponse, status_code=200)
async def consultar_terminos(handler: ConsultarTerminosHandler = Depends(get_handler)) -> TerminosResponse:
    return await handler.handle()
