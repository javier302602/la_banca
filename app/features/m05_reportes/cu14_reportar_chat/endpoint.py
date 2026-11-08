"""CU-14 — Reportar un chat. Controlador MVC (APIRouter), sin lógica de negocio."""
from fastapi import APIRouter, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.config.provider import get_config
from app.shared.db.mongo import get_database
from app.shared.domain.entities import MOTIVOS_REPORTE
from app.shared.security.session import SesionActual, get_sesion_actual, get_sesion_opcional
from app.shared.storage.image_storage import get_image_storage
from app.shared.web.plantillas import redirigir_a_login, render

from .handler import ReportarChatHandler
from .repository import MongoChatLecturaRepository, MongoReportarChatRepository
from .request import ReporteRequest, ReporteResponse

router = APIRouter(tags=["M05 Reportes"])


def get_handler(db: AsyncIOMotorDatabase = Depends(get_database)) -> ReportarChatHandler:
    return ReportarChatHandler(
        chats=MongoChatLecturaRepository(db),
        reportes=MongoReportarChatRepository(db),
        imagenes=get_image_storage(),
        config=get_config(),
        clock=get_clock(),
    )


@router.post("/api/chats/{chat_id}/reportes", response_model=ReporteResponse, status_code=201)
async def reportar_chat(
    chat_id: str,
    body: ReporteRequest,
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: ReportarChatHandler = Depends(get_handler),
) -> ReporteResponse:
    return await handler.handle(sesion.estudiante_id, chat_id, body)


@router.get("/chats/{chat_id}/reportar", include_in_schema=False)
async def pagina_reportar(request: Request, chat_id: str, sesion: SesionActual | None = Depends(get_sesion_opcional)):
    if sesion is None:
        return redirigir_a_login(request)
    return render(request, "m05_reportes/reportar.html", sesion, objeto="chat", motivos=list(MOTIVOS_REPORTE.values()), volver=f"/chats/{chat_id}", endpoint_api=f"/api/chats/{chat_id}/reportes")
