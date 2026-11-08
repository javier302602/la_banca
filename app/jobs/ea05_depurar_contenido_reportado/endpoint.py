"""EA-05 — Eliminar contenido reportado vencido. Controlador MVC (APIRouter), sin lógica de negocio."""
import hmac
import os

from fastapi import APIRouter, Depends, HTTPException, Header, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.storage.image_storage import get_image_storage

from .handler import DepurarContenidoReportadoHandler
from .repository import MongoDepurarReportesRepository

router = APIRouter(tags=["Jobs"])


def verificar_cron_secret(authorization: str | None = Header(default=None)) -> None:
    """Exige `Authorization: Bearer <CRON_SECRET>` (Vercel Cron). 401 si falta o no coincide."""
    secreto = os.environ.get("CRON_SECRET", "")
    esperado = f"Bearer {secreto}"
    if not secreto or authorization is None or not hmac.compare_digest(authorization, esperado):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autorizado")


def get_handler(db: AsyncIOMotorDatabase = Depends(get_database)) -> DepurarContenidoReportadoHandler:
    return DepurarContenidoReportadoHandler(
        reportes=MongoDepurarReportesRepository(db),
        imagenes=get_image_storage(),
        clock=get_clock(),
    )


@router.get("/jobs/ea05-depurar-contenido-reportado", status_code=200)
async def ejecutar(
    _: None = Depends(verificar_cron_secret),
    handler: DepurarContenidoReportadoHandler = Depends(get_handler),
) -> None:
    """Invocado por Vercel Cron (15 3 * * *)."""
    raise NotImplementedError
