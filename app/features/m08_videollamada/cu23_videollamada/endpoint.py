"""CU-23 — Videollamada. Página /videollamada y WebSocket /ws/videollamada (sin lógica de negocio).

Por cada conexión corren dos tareas:
- recibir: lee lo que manda el navegador (buscar, siguiente, colgar, senal, chat) y responde;
- atender: cada 0,3 s lee el buzón (emparejado, señales, chat, colgó) y, si espera pareja, intenta emparejar
  cada ~1 s. Al cerrarse la conexión se cuelga y se sale de la cola.
Mensajes del servidor al navegador: esperando · emparejado {sala, pareja, iniciador} · senal {datos} ·
chat {texto} · colgo · colgado · error {mensaje}.
"""
import asyncio
import json
import random

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect

from app.shared.clock import get_clock
from app.shared.config.provider import variable
from app.shared.db.mongo import base_de_datos
from app.shared.security.session import SesionActual, get_sesion_opcional, sesion_de_websocket
from app.shared.web.plantillas import redirigir_a_login, render

from .handler import Conexion, VideollamadaHandler
from .repository import MongoVideollamadaRepository

router = APIRouter(tags=["M08 Videollamada"])
CIERRE_SIN_SESION, CIERRE_SIN_PERFIL = 4401, 4403
INTERVALO_BUZON_S, INTERVALO_EMPAREJAR_S = 0.3, 1.0


def servidores_ice() -> list[dict]:
    """STUN (por omisión el público de Google) y TURN opcional, todo desde .env (coturn más adelante)."""
    stun = variable("WEBRTC_STUN_URLS", "stun:stun.l.google.com:19302") or ""
    servidores = [{"urls": [u.strip() for u in stun.split(",") if u.strip()]}] if stun.strip() else []
    turn = (variable("WEBRTC_TURN_URL") or "").strip()
    if turn:
        servidores.append({"urls": [u.strip() for u in turn.split(",")], "username": variable("WEBRTC_TURN_USUARIO") or "",
                           "credential": variable("WEBRTC_TURN_CLAVE") or ""})
    return servidores


@router.get("/videollamada", include_in_schema=False)
async def pagina_videollamada(request: Request, sesion: SesionActual | None = Depends(get_sesion_opcional)):
    if sesion is None:
        return redirigir_a_login(request)
    yo = await MongoVideollamadaRepository(base_de_datos()).buscar_participante(sesion.estudiante_id)
    perfil_completo = bool(yo and yo.nombre and yo.carrera)
    return render(request, "m08_videollamada/videollamada.html", sesion, perfil_completo=perfil_completo,
                  servidores_ice=json.dumps(servidores_ice()))


@router.websocket("/ws/videollamada")
async def videollamada(websocket: WebSocket) -> None:
    db = base_de_datos()
    sesion = await sesion_de_websocket(websocket, db)
    if sesion is None:
        await websocket.close(code=CIERRE_SIN_SESION)
        return
    handler = VideollamadaHandler(MongoVideollamadaRepository(db), get_clock())
    conexion = await handler.conectar(sesion.estudiante_id)
    if conexion is None:
        await websocket.close(code=CIERRE_SIN_PERFIL)  # falta nombre o carrera en el perfil
        return
    await websocket.accept()
    # Un candado por conexión: las dos tareas no cambian el estado a la vez (p. ej. «colgar» mientras se empareja)
    candado = asyncio.Lock()
    tareas = [asyncio.create_task(_recibir(websocket, handler, conexion, candado)),
              asyncio.create_task(_atender(websocket, handler, conexion, candado))]
    try:
        await asyncio.wait(tareas, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for tarea in tareas:
            tarea.cancel()
        async with candado:
            await handler.desconectar(conexion)


async def _enviar(websocket: WebSocket, mensajes: list[dict]) -> None:
    for mensaje in mensajes:
        await websocket.send_json(mensaje)


async def _recibir(websocket: WebSocket, handler: VideollamadaHandler, c: Conexion, candado: asyncio.Lock) -> None:
    acciones = {"buscar": handler.buscar, "siguiente": handler.siguiente, "colgar": handler.colgar}
    try:
        while True:
            datos = await websocket.receive_json()
            tipo = datos.get("tipo") if isinstance(datos, dict) else None
            async with candado:
                if tipo in acciones:
                    respuestas = await acciones[tipo](c)
                elif tipo in ("senal", "chat"):
                    respuestas = await handler.reenviar(c, datos)
                else:
                    respuestas = [{"tipo": "error", "mensaje": "Mensaje no reconocido"}]
            await _enviar(websocket, respuestas)
    except (WebSocketDisconnect, ValueError):  # ValueError: llegó algo que no es JSON
        return


async def _atender(websocket: WebSocket, handler: VideollamadaHandler, c: Conexion, candado: asyncio.Lock) -> None:
    proximo_intento = 0.0
    reloj = asyncio.get_running_loop()
    try:
        while True:
            async with candado:
                respuestas = await handler.leer_buzon(c)
                if c.estado == "esperando" and reloj.time() >= proximo_intento:
                    respuestas += await handler.intentar_emparejar(c)
                    # un poco de azar en el ritmo evita que dos personas que esperan choquen siempre a la vez
                    proximo_intento = reloj.time() + INTERVALO_EMPAREJAR_S * random.uniform(0.6, 1.4)
            await _enviar(websocket, respuestas)
            await asyncio.sleep(INTERVALO_BUZON_S)
    except (WebSocketDisconnect, RuntimeError):  # RuntimeError: se envió con la conexión ya cerrada
        return
