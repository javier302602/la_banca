"""CU-20 — Ver el perfil de una persona. Controlador MVC (APIRouter), sin lógica de negocio."""
from fastapi import APIRouter, Depends, Request, Response
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.db.mongo import get_database
from app.shared.security.session import SesionActual, get_sesion_actual, get_sesion_opcional
from app.shared.storage.image_storage import get_image_storage
from app.shared.web.plantillas import redirigir_a_login, render

from .handler import VerPerfilHandler
from .repository import MongoVerPerfilRepository
from .request import PerfilPublicoResponse

router = APIRouter(tags=["M07 Perfiles"])


def get_handler(db: AsyncDatabase = Depends(get_database)) -> VerPerfilHandler:
    return VerPerfilHandler(cuentas=MongoVerPerfilRepository(db), imagenes=get_image_storage())


@router.get("/api/perfiles/{nickname}", response_model=PerfilPublicoResponse, status_code=200)
async def ver_perfil(nickname: str, sesion: SesionActual = Depends(get_sesion_actual),
                     handler: VerPerfilHandler = Depends(get_handler)) -> PerfilPublicoResponse:
    return await handler.handle(sesion.estudiante_id, nickname)


@router.get("/api/perfiles/{nickname}/foto", status_code=200)
async def ver_foto(nickname: str, sesion: SesionActual = Depends(get_sesion_actual),
                   handler: VerPerfilHandler = Depends(get_handler)) -> Response:
    foto = await handler.foto(nickname)
    # La URL lleva ?v=<fecha de la foto>: al cambiarla cambia la URL, así que puede guardarse en caché
    return Response(foto.contenido, media_type=foto.mime_type,
                    headers={"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"})


@router.get("/perfiles/{nickname}", include_in_schema=False)
async def pagina_perfil(request: Request, nickname: str, sesion: SesionActual | None = Depends(get_sesion_opcional)):
    if sesion is None:
        return redirigir_a_login(request)
    return render(request, "m07_perfiles/ver_perfil.html", sesion, nickname=nickname)
