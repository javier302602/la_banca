"""CU-16 — Consultar términos de uso y política de privacidad. Controlador MVC (APIRouter)."""
from fastapi import APIRouter, Depends, Request

from app.shared.config.provider import variable
from app.shared.security.session import SesionActual, get_sesion_opcional
from app.shared.web.plantillas import render

from .handler import ConsultarTerminosHandler
from .repository import leer_terminos
from .request import TerminosResponse

router = APIRouter(tags=["M01 Acceso"])


def get_handler() -> ConsultarTerminosHandler:
    return ConsultarTerminosHandler(variable("TERMINOS_VERSION"), variable("TERMINOS_FECHA"), leer_terminos,
                                    variable("CANAL_ARCO"))


@router.get("/api/terminos", response_model=TerminosResponse, status_code=200)
async def consultar_terminos(handler: ConsultarTerminosHandler = Depends(get_handler)) -> TerminosResponse:
    return await handler.handle()


@router.get("/ayuda", include_in_schema=False)
async def pagina_ayuda(request: Request, sesion: SesionActual | None = Depends(get_sesion_opcional)):
    """Ayuda (WCAG 3.2.6 ayuda consistente, Nielsen H10): enlazada desde el pie de todas las páginas."""
    return render(request, "m01_acceso/ayuda.html", sesion)


@router.get("/terminos", include_in_schema=False)
async def pagina_terminos(request: Request, sesion: SesionActual | None = Depends(get_sesion_opcional),
                          handler: ConsultarTerminosHandler = Depends(get_handler)):
    return render(request, "m01_acceso/terminos.html", sesion, terminos=await handler.handle())
