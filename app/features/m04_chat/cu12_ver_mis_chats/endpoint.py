"""CU-12 — Ver mis chats activos y abrir uno. Controlador MVC (APIRouter), sin lógica de negocio."""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.config.provider import get_config
from app.shared.db.mongo import get_database
from app.shared.security.session import SesionActual, get_sesion_actual

from .handler import VerMisChatsHandler
from .repository import MongoVerMisChatsRepository
from .request import ChatDetalleResponse, ChatResumenResponse

router = APIRouter(tags=["M04 Chat"])


def get_handler(db: AsyncIOMotorDatabase = Depends(get_database)) -> VerMisChatsHandler:
    return VerMisChatsHandler(
        chats=MongoVerMisChatsRepository(db),
        config=get_config(),
        clock=get_clock(),
    )


@router.get("/chats", response_model=list[ChatResumenResponse], status_code=200)
async def ver_mis_chats(
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: VerMisChatsHandler = Depends(get_handler),
) -> list[ChatResumenResponse]:
    """Delegar en el handler."""
    raise NotImplementedError


@router.get("/chats/{chat_id}", response_model=ChatDetalleResponse, status_code=200)
async def abrir_chat(
    chat_id: str,
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: VerMisChatsHandler = Depends(get_handler),
) -> ChatDetalleResponse:
    """Delegar en el handler."""
    raise NotImplementedError
