"""CU-14 — Reportar un chat. Controlador MVC (APIRouter), sin lógica de negocio."""
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.config.provider import get_config
from app.shared.db.mongo import get_database
from app.shared.security.session import SesionActual, get_sesion_actual
from app.shared.storage.image_storage import get_image_storage

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
