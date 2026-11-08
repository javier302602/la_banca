"""CU-08 — Consultar el feed «Ahora». Controlador MVC (APIRouter), sin lógica de negocio.

Las actualizaciones automáticas del feed envían `X-Actualizacion-Automatica: 1` y no reinician la
inactividad de la sesión (RF-AUT-25).
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.db.mongo import get_database
from app.shared.domain.entities import TipoPublicacion
from app.shared.security.session import SesionActual, get_sesion_actual, get_sesion_opcional
from app.shared.web.plantillas import redirigir, redirigir_a_login, render

from .handler import ConsultarFeedHandler
from .repository import MongoConsultarFeedRepository
from .request import ConsultarFeedRequest, FeedResponse

router = APIRouter(tags=["M03 Feed"])


def get_handler(db: AsyncIOMotorDatabase = Depends(get_database)) -> ConsultarFeedHandler:
    return ConsultarFeedHandler(publicaciones=MongoConsultarFeedRepository(db), clock=get_clock())


@router.get("/api/feed", response_model=FeedResponse, status_code=200)
async def consultar_feed(
    body: Annotated[ConsultarFeedRequest, Query()],
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: ConsultarFeedHandler = Depends(get_handler),
) -> FeedResponse:
    return await handler.handle(sesion.estudiante_id, body)


@router.get("/", include_in_schema=False)
async def inicio(sesion: SesionActual | None = Depends(get_sesion_opcional)):
    return redirigir("/feed" if sesion else "/login")


@router.get("/feed", include_in_schema=False)
async def pagina_feed(request: Request, sesion: SesionActual | None = Depends(get_sesion_opcional)):
    if sesion is None:
        return redirigir_a_login(request)
    return render(request, "m03_feed/feed.html", sesion, tipos=[(t.value, t.value.capitalize()) for t in TipoPublicacion])
