"""CU-05 — Crear publicación. Controlador MVC (APIRouter), sin lógica de negocio."""
import json

from fastapi import APIRouter, Depends, Request
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.clock import get_clock
from app.shared.config.provider import get_config
from app.shared.db.mongo import get_database
from app.shared.domain.entities import MAX_IMAGENES_PUBLICACION, TAMANO_MAX_IMAGEN, TipoPublicacion
from app.shared.domain.errors import ErrorValidacion
from app.shared.storage.image_storage import get_image_storage
from app.shared.security.session import SesionActual, get_sesion_actual, get_sesion_opcional
from app.shared.web.plantillas import redirigir_a_login, render

from .handler import CrearPublicacionHandler
from .repository import MongoCrearPublicacionRepository
from .request import CrearPublicacionRequest, CupoResponse, PublicacionResponse

MSG_FORMULARIO = f"El formulario no es válido o tiene más de {MAX_IMAGENES_PUBLICACION} imágenes"

router = APIRouter(tags=["M02 Publicaciones"])


def get_handler(db: AsyncDatabase = Depends(get_database)) -> CrearPublicacionHandler:
    return CrearPublicacionHandler(
        publicaciones=MongoCrearPublicacionRepository(db),
        config=get_config(),
        clock=get_clock(),
        imagenes=get_image_storage(),
    )


async def leer_solicitud(request: Request) -> tuple[CrearPublicacionRequest, list[bytes]]:
    """JSON (sin imágenes, como en v1) o multipart/form-data con el campo «imagenes» (hasta 3 archivos)."""
    if request.headers.get("content-type", "").startswith("multipart/form-data"):
        # max_files: una más que el máximo, para responder «hasta 3 imágenes» en lugar de un error genérico
        try:
            formulario = await request.form(max_files=MAX_IMAGENES_PUBLICACION + 1, max_fields=10)
        except StarletteHTTPException:
            raise ErrorValidacion(MSG_FORMULARIO, codigo="formulario_invalido", campo="imagenes") from None
        try:
            datos = {k: v for k, v in formulario.items() if not isinstance(v, UploadFile)}
            imagenes = []
            for archivo in formulario.getlist("imagenes"):
                if isinstance(archivo, UploadFile) and archivo.filename:
                    contenido = await archivo.read(TAMANO_MAX_IMAGEN + 1)
                    if contenido:
                        imagenes.append(contenido)
        finally:
            await formulario.close()
        return CrearPublicacionRequest.model_validate(datos), imagenes
    try:
        datos = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ErrorValidacion("El cuerpo de la solicitud no es válido", codigo="cuerpo_invalido") from None
    if not isinstance(datos, dict):
        raise ErrorValidacion("El cuerpo de la solicitud no es válido", codigo="cuerpo_invalido")
    return CrearPublicacionRequest.model_validate(datos), []


@router.post("/api/publicaciones", response_model=PublicacionResponse, status_code=201,
             openapi_extra={"requestBody": {"content": {
                 "application/json": {"schema": CrearPublicacionRequest.model_json_schema()},
                 "multipart/form-data": {"schema": {"type": "object", "properties": {
                     "tipo": {"type": "string"}, "titulo": {"type": "string"}, "descripcion": {"type": "string"},
                     "imagenes": {"type": "array", "maxItems": MAX_IMAGENES_PUBLICACION,
                                  "items": {"type": "string", "format": "binary"}}}}}}}})
async def crear_publicacion(
    request: Request,
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: CrearPublicacionHandler = Depends(get_handler),
) -> PublicacionResponse:
    body, imagenes = await leer_solicitud(request)
    return await handler.handle(sesion.estudiante_id, sesion.nickname, body, imagenes)


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
    return render(request, "m02_publicaciones/crear_publicacion.html", sesion, tipos=[t.value for t in TipoPublicacion])
