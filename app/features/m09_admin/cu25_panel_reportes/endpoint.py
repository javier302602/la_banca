"""CU-25 — Panel de reportes. Página /admin y API /api/admin/reportes (solo administradores)."""
from fastapi import APIRouter, Depends, Query, Request, Response
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.db.mongo import get_database
from app.shared.domain.entities import EstadoReporte
from app.shared.security.session import SesionActual, get_sesion_admin, get_sesion_opcional
from app.shared.storage.image_storage import get_image_storage
from app.shared.web.plantillas import redirigir, redirigir_a_login, render

from .handler import PanelReportesHandler
from .repository import MongoAdminRepository
from .request import PanelResponse, PendientesResponse

router = APIRouter(tags=["M09 Administración"])


def get_handler(db: AsyncDatabase = Depends(get_database)) -> PanelReportesHandler:
    return PanelReportesHandler(MongoAdminRepository(db), get_image_storage())


@router.get("/api/admin/reportes", response_model=PanelResponse, status_code=200)
async def listar_reportes(estado: EstadoReporte | None = Query(default=EstadoReporte.PENDIENTE),
                          todos: bool = Query(default=False),
                          sesion: SesionActual = Depends(get_sesion_admin),
                          handler: PanelReportesHandler = Depends(get_handler)) -> PanelResponse:
    return await handler.listar(None if todos else estado)


@router.get("/api/admin/reportes/pendientes", response_model=PendientesResponse, status_code=200)
async def contar_pendientes(sesion: SesionActual = Depends(get_sesion_admin),
                            handler: PanelReportesHandler = Depends(get_handler)) -> PendientesResponse:
    return await handler.pendientes()


@router.get("/api/admin/reportes/{origen}/{reporte_id}/imagenes/{indice}", status_code=200)
async def ver_imagen_retenida(origen: str, reporte_id: str, indice: int,
                              sesion: SesionActual = Depends(get_sesion_admin),
                              handler: PanelReportesHandler = Depends(get_handler)) -> Response:
    contenido, mime = await handler.imagen(origen, reporte_id, indice)
    return Response(contenido, media_type=mime, headers={"Cache-Control": "private, no-store",
                                                         "X-Content-Type-Options": "nosniff"})


@router.get("/admin", include_in_schema=False)
async def pagina_admin(request: Request, sesion: SesionActual | None = Depends(get_sesion_opcional)):
    if sesion is None:
        return redirigir_a_login(request)
    if not sesion.es_admin:
        return redirigir("/feed")
    return render(request, "m09_admin/panel.html", sesion)
