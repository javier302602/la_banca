"""CU-12 — Ver mis chats activos y abrir uno. Controlador MVC (APIRouter), sin lógica de negocio.

El sondeo de 1 s del chat abierto envía `X-Actualizacion-Automatica: 1` y `despues_de`, de modo que no
reinicia la inactividad de la sesión (RF-AUT-25) y solo trae mensajes nuevos.
"""
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request, Response
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.clock import get_clock
from app.shared.config.provider import get_config
from app.shared.db.mongo import get_database
from app.shared.db.perfiles import MongoPerfilesPublicosRepository
from app.shared.security.session import SesionActual, get_sesion_actual, get_sesion_opcional
from app.shared.storage.image_storage import get_image_storage
from app.shared.web.plantillas import redirigir_a_login, render

from .handler import VerMisChatsHandler
from .repository import MongoVerMisChatsRepository
from .request import AbrirChatRequest, ChatDetalleResponse, MisChatsResponse

router = APIRouter(tags=["M04 Chat"])


def get_handler(db: AsyncDatabase = Depends(get_database)) -> VerMisChatsHandler:
    return VerMisChatsHandler(
        chats=MongoVerMisChatsRepository(db),
        imagenes=get_image_storage(),
        config=get_config(),
        clock=get_clock(),
        cuentas=MongoPerfilesPublicosRepository(db),
    )


@router.get("/api/chats", response_model=MisChatsResponse, status_code=200)
async def ver_mis_chats(
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: VerMisChatsHandler = Depends(get_handler),
) -> MisChatsResponse:
    return await handler.handle(sesion.estudiante_id)


@router.get("/api/chats/{chat_id}", response_model=ChatDetalleResponse, status_code=200)
async def abrir_chat(
    chat_id: str,
    body: Annotated[AbrirChatRequest, Query()],
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: VerMisChatsHandler = Depends(get_handler),
) -> ChatDetalleResponse:
    return await handler.abrir(sesion.estudiante_id, chat_id, body)


@router.get("/api/chats/{chat_id}/mensajes/{mensaje_id}/imagen", status_code=200)
async def ver_imagen(
    chat_id: str,
    mensaje_id: str,
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: VerMisChatsHandler = Depends(get_handler),
) -> Response:
    imagen = await handler.imagen(sesion.estudiante_id, chat_id, mensaje_id)
    return Response(imagen.contenido, media_type=imagen.mime_type,
                    headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/api/chats/{chat_id}/mensajes/{mensaje_id}/documento", status_code=200)
async def descargar_documento(
    chat_id: str,
    mensaje_id: str,
    sesion: SesionActual = Depends(get_sesion_actual),
    handler: VerMisChatsHandler = Depends(get_handler),
) -> Response:
    """Siempre como descarga (attachment) y sin que el navegador adivine el tipo (nosniff): un documento nunca
    se interpreta como página dentro del sitio."""
    d = await handler.documento(sesion.estudiante_id, chat_id, mensaje_id)
    # RFC 6266 / 5987. Con un nombre no ASCII solo se envía filename*: algunos navegadores (WebKit) prefieren
    # la forma simple si existe, y esa no puede llevar tildes ni «ñ»
    disposicion = f"attachment; filename*=UTF-8''{quote(d.nombre)}"
    if d.nombre.isascii():
        disposicion = f'attachment; filename="{d.nombre.replace(chr(34), "_")}"; ' + disposicion.removeprefix("attachment; ")
    tipo = f"{d.mime_type}; charset=utf-8" if d.mime_type == "text/plain" else d.mime_type
    return Response(d.contenido, media_type=tipo, headers={
        "Content-Disposition": disposicion, "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-store", "Content-Security-Policy": "default-src 'none'; sandbox"})


@router.get("/chats", include_in_schema=False)
async def pagina_mis_chats(request: Request, sesion: SesionActual | None = Depends(get_sesion_opcional)):
    if sesion is None:
        return redirigir_a_login(request)
    return render(request, "m04_chat/mis_chats.html", sesion)


@router.get("/chats/{chat_id}", include_in_schema=False)
async def pagina_chat(request: Request, chat_id: str, sesion: SesionActual | None = Depends(get_sesion_opcional)):
    if sesion is None:
        return redirigir_a_login(request)
    return render(request, "m04_chat/chat.html", sesion, chat_id=chat_id)
