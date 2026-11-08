"""CU-16 — Consultar términos de uso y política de privacidad. Controlador MVC (APIRouter), sin lógica de negocio."""

from fastapi import APIRouter, Depends

from app.shared.config.provider import get_config

from .handler import ConsultarTerminosHandler
from .request import TerminosResponse

router = APIRouter(tags=["M01 Acceso"])


def get_handler() -> ConsultarTerminosHandler:
    return ConsultarTerminosHandler(
        config=get_config(),
    )


@router.get("/terminos", response_model=TerminosResponse, status_code=200)
async def consultar_terminos(
    handler: ConsultarTerminosHandler = Depends(get_handler),
) -> TerminosResponse:
    """Delegar en el handler."""
    raise NotImplementedError
