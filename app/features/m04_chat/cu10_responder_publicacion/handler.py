"""CU-10 — Responder a una publicación. Caso de uso (handler).

RF: RF-CHT-01–10, RF-CHT-23, RF-CHT-24, RF-CHT-26
Crea un único chat 1 a 1 por (publicación, usuario) con el primer mensaje (texto ≤ 500 y/o imagen JPG/PNG/WebP ≤ 5 MB). El chat expira tras 24 h de inactividad (INACTIVIDAD_CHAT).

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from app.shared.domain.contracts import IChatRepository, IClock, IPublicationRepository, ImageStorage

from .request import ChatCreadoResponse, MensajeEntrante


class ResponderPublicacionHandler:
    def __init__(self, publicaciones: IPublicationRepository, chats: IChatRepository, imagenes: ImageStorage, clock: IClock) -> None:
        self._publicaciones = publicaciones
        self._chats = chats
        self._imagenes = imagenes
        self._clock = clock

    async def handle(self, estudiante_id: str, publicacion_id: str, body: MensajeEntrante) -> ChatCreadoResponse:
        """Ejecuta el caso de uso."""
        raise NotImplementedError
