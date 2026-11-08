"""CU-08 — Consultar el feed «Ahora». Controlador MVC (APIRouter), sin lógica de negocio."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.security.session import SesionActual, get_sesion_actual

from .handler import ConsultarFeedHandler
from .repository import MongoConsultarFeedRepository
from .request import ConsultarFeedRequest, FeedResponse

router = APIRouter(tags=["M03 Feed"])


def get_handler(db: AsyncIOMotorDatabase = Depends(get_database)) -> ConsultarFeedHandler:
    return ConsultarFeedHandler(
        publicaciones=MongoConsultarFeedRepository(db),
        clock=get_clock(),
    )


@router.get("/feed", response_model=FeedResponse, status_code=200)
async def consultar_feed(
    body: Annotated[ConsultarFeedRequest, Query()],
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: ConsultarFeedHandler = Depends(get_handler),
) -> FeedResponse:
    """Delegar en el handler."""
    raise NotImplementedError
