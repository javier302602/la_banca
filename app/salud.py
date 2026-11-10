"""/api/salud — estado del servicio para monitores y healthchecks (Docker, Caddy, RNF-DIS-01).

Responde 200 con la versión cuando la base de datos contesta; 503 si no está disponible o configurada.
No requiere sesión y no expone datos de usuarios.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.shared.version import VERSION

router = APIRouter(tags=["Salud"])


async def estado_base() -> str:
    from pymongo.errors import PyMongoError

    from app.shared.db.mongo import base_de_datos

    try:
        await base_de_datos().command("ping")
        return "ok"
    except RuntimeError:  # MONGO_URI sin configurar
        return "no_configurada"
    except PyMongoError:
        return "no_disponible"


@router.get("/api/salud")
async def salud() -> JSONResponse:
    base = await estado_base()
    ok = base == "ok"
    cuerpo = {"estado": "ok" if ok else "degradado", "version": VERSION, "base_de_datos": base}
    return JSONResponse(cuerpo, status_code=200 if ok else 503, headers={"Cache-Control": "no-store"})
