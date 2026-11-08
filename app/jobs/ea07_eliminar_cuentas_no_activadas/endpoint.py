"""EA-07 — Eliminar las cuentas no activadas. Invocado por Vercel Cron (ver vercel.json)."""
import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.clock import get_clock
from app.shared.db.mongo import get_database

from .handler import EliminarCuentasNoActivadasHandler
from .repository import MongoEliminarCuentasRepository

router = APIRouter(tags=["Jobs"])


def verificar_cron_secret(authorization: str | None = Header(default=None)) -> None:
    """Exige `Authorization: Bearer <CRON_SECRET>` (Vercel Cron). 401 si falta o no coincide."""
    secreto = os.environ.get("CRON_SECRET", "")
    esperado = f"Bearer {secreto}"
    if not secreto or authorization is None or not hmac.compare_digest(authorization, esperado):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autorizado")


def get_handler(db: AsyncDatabase = Depends(get_database)) -> EliminarCuentasNoActivadasHandler:
    return EliminarCuentasNoActivadasHandler(cuentas=MongoEliminarCuentasRepository(db), clock=get_clock())


@router.get("/jobs/ea07-eliminar-cuentas-no-activadas", status_code=200)
async def ejecutar(
    _: None = Depends(verificar_cron_secret),
    handler: EliminarCuentasNoActivadasHandler = Depends(get_handler),
) -> dict[str, int]:
    return await handler.handle()
