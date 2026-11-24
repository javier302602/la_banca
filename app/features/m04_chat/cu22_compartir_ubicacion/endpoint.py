"""CU-22 — Compartir ubicación. WebSocket /ws/chats/{chat_id}/ubicacion (sin lógica de negocio).

Dos tareas en paralelo por conexión:
- recibir: lee lo que envía este navegador (posición o «detener») y lo guarda con el handler;
- avisar: cada 2 s mira la ubicación de la otra persona y la envía si cambió (o avisa que dejó de compartir).
Al cerrarse la conexión se borra la ubicación propia.
"""
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.shared.clock import get_clock
from app.shared.db.mongo import base_de_datos
from app.shared.security.session import SesionActual, sesion_de_websocket

from .handler import CompartirUbicacionHandler
from .repository import MongoChatUbicacionRepository, MongoUbicacionRepository
from .request import DetenerEntrante, PosicionEntrante

router = APIRouter(tags=["M04 Chat"])
INTERVALO_AVISO_S = 2
# Códigos de cierre propios (rango 4000–4999 del protocolo WebSocket)
CIERRE_SIN_SESION, CIERRE_SIN_CHAT = 4401, 4404


@router.websocket("/ws/chats/{chat_id}/ubicacion")
async def compartir_ubicacion(websocket: WebSocket, chat_id: str) -> None:
    db = base_de_datos()
    sesion = await sesion_de_websocket(websocket, db)
    if sesion is None:
        await websocket.close(code=CIERRE_SIN_SESION)
        return
    handler = CompartirUbicacionHandler(MongoChatUbicacionRepository(db), MongoUbicacionRepository(db), get_clock())
    chat = await handler.chat_permitido(sesion.estudiante_id, chat_id)
    if chat is None:
        await websocket.close(code=CIERRE_SIN_CHAT)
        return
    await websocket.accept()
    tareas = [asyncio.create_task(_recibir(websocket, handler, chat, sesion)),
              asyncio.create_task(_avisar(websocket, handler, chat, sesion))]
    try:
        await asyncio.wait(tareas, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for tarea in tareas:
            tarea.cancel()
        await handler.detener(chat.id, sesion.estudiante_id)  # al salir de la página deja de compartir


async def _recibir(websocket: WebSocket, handler: CompartirUbicacionHandler, chat, sesion: SesionActual) -> None:
    try:
        while True:
            datos = await websocket.receive_json()
            tipo = datos.get("tipo") if isinstance(datos, dict) else None
            try:
                if tipo == "posicion":
                    await handler.guardar(chat, sesion.estudiante_id, sesion.nickname, PosicionEntrante(**datos))
                elif tipo == "detener":
                    DetenerEntrante(**datos)
                    await handler.detener(chat.id, sesion.estudiante_id)
                else:
                    await websocket.send_json({"tipo": "error", "mensaje": "Mensaje no reconocido"})
            except ValidationError:
                await websocket.send_json({"tipo": "error", "mensaje": "La ubicación no es válida"})
    except (WebSocketDisconnect, ValueError):  # ValueError: llegó algo que no es JSON
        return


async def _avisar(websocket: WebSocket, handler: CompartirUbicacionHandler, chat, sesion: SesionActual) -> None:
    ultima = None
    try:
        while True:
            if await handler.chat_permitido(sesion.estudiante_id, chat.id) is None:  # el chat expiró
                await websocket.close(code=CIERRE_SIN_CHAT)
                return
            otra = await handler.de_la_otra_persona(chat, sesion.estudiante_id)
            if otra is not None and otra.actualizado != ultima:
                ultima = otra.actualizado
                await websocket.send_json({"tipo": "posicion", "nickname": otra.nickname, "lat": otra.lat,
                                           "lng": otra.lng, "precision": otra.precision,
                                           "actualizado": otra.actualizado.isoformat()})
            elif otra is None and ultima is not None:
                ultima = None
                await websocket.send_json({"tipo": "detenido"})
            await asyncio.sleep(INTERVALO_AVISO_S)
    except (WebSocketDisconnect, RuntimeError):  # RuntimeError: se envió con la conexión ya cerrada
        return
