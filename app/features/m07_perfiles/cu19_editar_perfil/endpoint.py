"""CU-19 — Editar mi perfil. Controlador MVC (APIRouter), sin lógica de negocio.

La página /perfil (CU-04) reúne el nickname y estos datos.
"""
from fastapi import APIRouter, Depends, File, UploadFile
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.domain.perfiles import TAMANO_MAX_FOTO
from app.shared.security.session import SesionActual, get_sesion_actual
from app.shared.storage.image_storage import get_image_storage, leer_imagen_subida

from .handler import EditarPerfilHandler
from .repository import MongoEditarPerfilRepository
from .request import EditarPerfilRequest, MiPerfilResponse

router = APIRouter(tags=["M07 Perfiles"])


def get_handler(db: AsyncDatabase = Depends(get_database)) -> EditarPerfilHandler:
    return EditarPerfilHandler(cuentas=MongoEditarPerfilRepository(db), imagenes=get_image_storage(),
                               clock=get_clock())


@router.get("/api/cuentas/me/perfil", response_model=MiPerfilResponse, status_code=200)
async def ver_mi_perfil(sesion: SesionActual = Depends(get_sesion_actual),
                        handler: EditarPerfilHandler = Depends(get_handler)) -> MiPerfilResponse:
    return await handler.ver(sesion.estudiante_id)


@router.patch("/api/cuentas/me/perfil", response_model=MiPerfilResponse, status_code=200)
async def editar_perfil(body: EditarPerfilRequest, sesion: SesionActual = Depends(get_sesion_actual),
                        handler: EditarPerfilHandler = Depends(get_handler)) -> MiPerfilResponse:
    return await handler.actualizar(sesion.estudiante_id, body)


@router.put("/api/cuentas/me/foto", response_model=MiPerfilResponse, status_code=200)
async def subir_foto(foto: UploadFile | None = File(default=None), sesion: SesionActual = Depends(get_sesion_actual),
                     handler: EditarPerfilHandler = Depends(get_handler)) -> MiPerfilResponse:
    return await handler.subir_foto(sesion.estudiante_id, await leer_imagen_subida(foto, TAMANO_MAX_FOTO))


@router.delete("/api/cuentas/me/foto", response_model=MiPerfilResponse, status_code=200)
async def quitar_foto(sesion: SesionActual = Depends(get_sesion_actual),
                      handler: EditarPerfilHandler = Depends(get_handler)) -> MiPerfilResponse:
    return await handler.quitar_foto(sesion.estudiante_id)
