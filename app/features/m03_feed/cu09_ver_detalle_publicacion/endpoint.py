"""CU-09 — Ver detalle de una publicación. Controlador MVC (APIRouter), sin lógica de negocio."""
from fastapi import APIRouter, Depends, Request
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.security.session import SesionActual, get_sesion_actual, get_sesion_opcional
from app.shared.web.plantillas import redirigir_a_login, render

from .handler import VerDetallePublicacionHandler
from .repository import MongoChatExistenteRepository, MongoVerDetallePublicacionRepository
from .request import DetallePublicacionResponse

router = APIRouter(tags=["M03 Feed"])


def get_handler(db: AsyncDatabase = Depends(get_database)) -> VerDetallePublicacionHandler:
    return VerDetallePublicacionHandler(
        publicaciones=MongoVerDetallePublicacionRepository(db),
        chats=MongoChatExistenteRepository(db),
        clock=get_clock(),
    )


@router.get("/api/publicaciones/{publicacion_id}", response_model=DetallePublicacionResponse, status_code=200)
async def ver_detalle_publicacion(
    publicacion_id: str,
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: VerDetallePublicacionHandler = Depends(get_handler),
) -> DetallePublicacionResponse:
    return await handler.handle(sesion.estudiante_id, publicacion_id)


@router.get("/publicaciones/{publicacion_id}", include_in_schema=False)
async def pagina_detalle(request: Request, publicacion_id: str, sesion: SesionActual | None = Depends(get_sesion_opcional)):
    if sesion is None:
        return redirigir_a_login(request)
    return render(request, "m03_feed/detalle_publicacion.html", sesion, publicacion_id=publicacion_id)
