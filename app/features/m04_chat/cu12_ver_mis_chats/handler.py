"""CU-12 — Ver mis chats activos y abrir uno. Caso de uso (handler).

RF: RF-CHT-15, RF-CHT-18, RF-CHT-19, RF-CHT-21, RF-CHT-25
EA-04 (Avisar expiración próxima; RF-CHT-12, RF-CHT-14) se calcula al abrir: se activa el aviso cuando el tiempo restante ≤ anticipación configurada (inicial 10 min). Un chat expirado se bloquea.

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from datetime import datetime

from app.shared.domain.entities import Chat
from app.shared.domain.contracts import IChatRepository, IClock, IConfigurationProvider

from .request import ChatDetalleResponse, ChatResumenResponse


class VerMisChatsHandler:
    def __init__(self, chats: IChatRepository, config: IConfigurationProvider, clock: IClock) -> None:
        self._chats = chats
        self._config = config
        self._clock = clock

    async def handle(self, estudiante_id: str) -> list[ChatResumenResponse]:
        """Ejecuta el caso de uso."""
        raise NotImplementedError

    async def abrir(self, estudiante_id: str, chat_id: str) -> ChatDetalleResponse:
        """Ejecuta el caso de uso."""
        raise NotImplementedError

    def _calcular_aviso(self, chat: Chat, ahora: datetime) -> tuple[int, bool]:
        """EA-04 — Devuelve (segundos_restantes, aviso_expiracion)."""
        raise NotImplementedError
