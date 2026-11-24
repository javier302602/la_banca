"""CU-22 — Compartir ubicación GPS en tiempo real. Caso de uso (handler).

Flujo:
1. El navegador pide permiso (Geolocation API) y abre el WebSocket del chat.
2. Cada posición que envía se guarda como la «ubicación en vivo» del estudiante en ese chat.
3. El WebSocket de la otra persona la lee y se la muestra. Solo los dos participantes del chat la ven.
4. «Dejar de compartir», cerrar la página o que expire el chat la borran. Por si acaso, cada ubicación vence
   sola a los 2 minutos sin actualizarse (índice TTL): nunca queda un historial de posiciones.
"""
from app.shared.domain.contracts import IChatRepository, IClock, IUbicacionRepository
from app.shared.domain.entities import VIGENCIA_UBICACION, Chat, UbicacionEnVivo

from .request import PosicionEntrante


class CompartirUbicacionHandler:
    def __init__(self, chats: IChatRepository, ubicaciones: IUbicacionRepository, clock: IClock) -> None:
        self._chats = chats
        self._ubicaciones = ubicaciones
        self._clock = clock

    async def chat_permitido(self, estudiante_id: str, chat_id: str) -> Chat | None:
        """El chat si existe, está activo y el estudiante es participante; si no, None."""
        chat = await self._chats.buscar_por_id(chat_id)
        if chat is None or estudiante_id not in chat.participantes or not chat.activo(self._clock.ahora()):
            return None
        return chat

    async def guardar(self, chat: Chat, estudiante_id: str, nickname: str, posicion: PosicionEntrante) -> None:
        ahora = self._clock.ahora()
        await self._ubicaciones.guardar(UbicacionEnVivo(
            chat_id=chat.id, estudiante_id=estudiante_id, nickname=nickname, lat=posicion.lat, lng=posicion.lng,
            precision=posicion.precision, actualizado=ahora, expira_en=ahora + VIGENCIA_UBICACION))

    async def detener(self, chat_id: str, estudiante_id: str) -> None:
        await self._ubicaciones.borrar(chat_id, estudiante_id)

    async def de_la_otra_persona(self, chat: Chat, estudiante_id: str) -> UbicacionEnVivo | None:
        otra = next((p for p in chat.participantes if p != estudiante_id), None)
        ubicacion = await self._ubicaciones.buscar(chat.id, otra) if otra else None
        if ubicacion is None or ubicacion.expira_en <= self._clock.ahora():
            return None
        return ubicacion
