"""CU-05 — Crear publicación. Controlador MVC (APIRouter), sin lógica de negocio."""
from fastapi import APIRouter, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.config.provider import get_config
from app.shared.db.mongo import get_database
from app.shared.domain.entities import TipoPublicacion
from app.shared.security.session import SesionActual, get_sesion_actual, get_sesion_opcional
from app.shared.web.plantillas import redirigir_a_login, render

from .handler import CrearPublicacionHandler
from .repository import MongoCrearPublicacionRepository
from .request import CrearPublicacionRequest, CupoResponse, PublicacionResponse

router = APIRouter(tags=["M02 Publicaciones"])


def get_handler(db: AsyncIOMotorDatabase = Depends(get_database)) -> CrearPublicacionHandler:
    return CrearPublicacionHandler(
        publicaciones=MongoCrearPublicacionRepository(db),
        config=get_config(),
        clock=get_clock(),
    )


@router.post("/api/publicaciones", response_model=PublicacionResponse, status_code=201)
async def crear_publicacion(
    body: CrearPublicacionRequest,
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: CrearPublicacionHandler = Depends(get_handler),
) -> PublicacionResponse:
    return await handler.handle(sesion.estudiante_id, sesion.nickname, body)


@router.get("/api/publicaciones/cupo", response_model=CupoResponse, status_code=200)
async def consultar_cupo(
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: CrearPublicacionHandler = Depends(get_handler),
) -> CupoResponse:
    return await handler.cupo(sesion.estudiante_id)


@router.get("/publicaciones/nueva", include_in_schema=False)
async def pagina_crear(request: Request, sesion: SesionActual | None = Depends(get_sesion_opcional)):
    if sesion is None:
        return redirigir_a_login(request)
    return render(request, "m02_publicaciones/crear_publicacion.html", sesion, tipos=[(t.value, t.value.capitalize()) for t in TipoPublicacion])
