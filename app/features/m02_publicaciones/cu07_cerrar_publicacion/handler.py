"""CU-07 — Cerrar publicación manualmente. Caso de uso (handler).

RF: RF-PUB-08, RF-PUB-11, RF-CHT-17
Solo el autor. Los chats ya originados continúan su ciclo de vida independiente (RF-CHT-17).

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from app.shared.domain.contracts import IClock, IPublicationRepository


class CerrarPublicacionHandler:
    def __init__(self, publicaciones: IPublicationRepository, clock: IClock) -> None:
        self._publicaciones = publicaciones
        self._clock = clock

    async def handle(self, estudiante_id: str, publicacion_id: str) -> None:
        """Ejecuta el caso de uso."""
        raise NotImplementedError
