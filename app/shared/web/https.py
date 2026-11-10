"""RNF-SEG-03: toda comunicación por HTTPS.

Con ENTORNO=produccion:
- una solicitud que llegó por HTTP se redirige (308) a la misma URL con https;
- las respuestas por HTTPS llevan Strict-Transport-Security (HSTS), para que el navegador no vuelva a usar HTTP.
El esquema original se lee de X-Forwarded-Proto, que fija el proxy de la plataforma (Vercel) al terminar TLS.
La versión de TLS (≥ 1.2) la negocia la plataforma, no la app: depende del despliegue.
"""
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import RedirectResponse

HSTS = "max-age=63072000; includeSubDomains"  # 2 años


def en_produccion() -> bool:
    import os

    return (os.environ.get("ENTORNO") or "").strip().lower() == "produccion"


def esquema_original(request: Request) -> str:
    reenviado = request.headers.get("x-forwarded-proto", "")
    return (reenviado.split(",")[0].strip() or request.url.scheme).lower()


async def forzar_https(request: Request, siguiente: Callable[[Request], Awaitable[Response]]) -> Response:
    if not en_produccion():
        return await siguiente(request)
    if esquema_original(request) == "http":
        return RedirectResponse(str(request.url.replace(scheme="https")), status_code=308)
    respuesta = await siguiente(request)
    respuesta.headers.setdefault("Strict-Transport-Security", HSTS)
    return respuesta
