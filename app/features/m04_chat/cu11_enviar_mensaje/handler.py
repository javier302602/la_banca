"""CU-11 — Enviar mensaje en un chat. Caso de uso (handler).

RF: RF-CHT-08–12, RF-CHT-15, RF-CHT-20, RF-CHT-22, RF-CHT-25, RF-CHT-26
Solo participantes de un chat vigente. Cada mensaje reinicia el conteo de inactividad (24 h).

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from app.shared.domain.contracts import IChatRepository, IClock, ImageStorage

from .request import MensajeEntrante, MensajeResponse


class EnviarMensajeHandler:
    def __init__(self, chats: IChatRepository, imagenes: ImageStorage, clock: IClock) -> None:
        self._chats = chats
        self._imagenes = imagenes
        self._clock = clock

    async def handle(self, estudiante_id: str, chat_id: str, body: MensajeEntrante) -> MensajeResponse:
        """Ejecuta el caso de uso."""
        raise NotImplementedError
