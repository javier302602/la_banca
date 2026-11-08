"""CU-04 — Editar nickname. Controlador MVC (APIRouter), sin lógica de negocio."""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.security.session import SesionActual, get_sesion_actual

from .handler import EditarNicknameHandler
from .repository import MongoEditarNicknameRepository
from .request import EditarNicknameRequest, NicknameResponse

router = APIRouter(tags=["M01 Acceso"])


def get_handler(db: AsyncIOMotorDatabase = Depends(get_database)) -> EditarNicknameHandler:
    return EditarNicknameHandler(
        cuentas=MongoEditarNicknameRepository(db),
        clock=get_clock(),
    )


@router.patch("/cuentas/me/nickname", response_model=NicknameResponse, status_code=200)
async def editar_nickname(
    body: EditarNicknameRequest,
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: EditarNicknameHandler = Depends(get_handler),
) -> NicknameResponse:
    """Delegar en el handler."""
    raise NotImplementedError
