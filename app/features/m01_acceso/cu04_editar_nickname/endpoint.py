"""CU-04 — Editar nickname. Controlador MVC (APIRouter), sin lógica de negocio."""
from fastapi import APIRouter, Depends, Request
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.domain.perfiles import GRUPOS_AVATAR
from app.shared.security.session import SesionActual, get_sesion_actual, get_sesion_opcional
from app.shared.web.plantillas import redirigir_a_login, render

from .handler import EditarNicknameHandler
from .repository import MongoEditarNicknameRepository
from .request import EditarNicknameRequest, NicknameResponse

router = APIRouter(tags=["M01 Acceso"])


def get_handler(db: AsyncDatabase = Depends(get_database)) -> EditarNicknameHandler:
    return EditarNicknameHandler(cuentas=MongoEditarNicknameRepository(db), clock=get_clock())


@router.patch("/api/cuentas/me/nickname", response_model=NicknameResponse, status_code=200)
async def editar_nickname(
    body: EditarNicknameRequest,
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: EditarNicknameHandler = Depends(get_handler),
) -> NicknameResponse:
    return await handler.handle(sesion.estudiante_id, body)


@router.get("/perfil", include_in_schema=False)
async def pagina_perfil(request: Request, sesion: SesionActual | None = Depends(get_sesion_opcional)):
    if sesion is None:
        return redirigir_a_login(request)
    return render(request, "m01_acceso/editar_nickname.html", sesion, grupos_avatar=GRUPOS_AVATAR)
