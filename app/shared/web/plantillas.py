"""Plantillas Jinja2 compartidas por las vistas de los slices (MVC).

Jinja2Templates activa el autoescape para .html: todo texto de usuario se muestra literal (RNF-SEG-05).
"""
from pathlib import Path

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.shared.security.session import SesionActual
from app.shared.web.i18n import IDIOMA_ACTIVO, ZONA_HORARIA, catalogo_js, t

DIRECTORIO = Path(__file__).resolve().parents[3] / "web" / "templates"
plantillas = Jinja2Templates(directory=DIRECTORIO)
# i18n: todas las plantillas toman sus textos del catálogo (web/i18n/es-PE.json)
plantillas.env.globals.update(t=t, idioma=IDIOMA_ACTIVO, zona_horaria=ZONA_HORARIA, catalogo_js=catalogo_js())


def render(request: Request, nombre: str, sesion: SesionActual | None = None, **contexto):
    return plantillas.TemplateResponse(request, nombre, {"sesion": sesion, **contexto},
                                       headers={"Cache-Control": "no-store"})


def redirigir_a_login(request: Request) -> RedirectResponse:
    """Sin sesión válida: al inicio de sesión, con el aviso de inactividad si corresponde (RF-AUT-23)."""
    motivo = getattr(request.state, "motivo_sin_sesion", None)
    destino = "/login?motivo=inactividad" if motivo == "sesion_expirada" else "/login"
    return RedirectResponse(destino, status_code=303)


def redirigir(destino: str) -> RedirectResponse:
    return RedirectResponse(destino, status_code=303)
