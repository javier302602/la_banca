"""CU-06 — Ver mis publicaciones activas. Caso de uso (handler).

RF: RF-PUB-10, RF-FED-09
Lista solo las publicaciones vigentes del autor con su tiempo restante.

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from app.shared.domain.contracts import IClock, IPublicationRepository

from .request import MiPublicacionResponse


class VerMisPublicacionesHandler:
    def __init__(self, publicaciones: IPublicationRepository, clock: IClock) -> None:
        self._publicaciones = publicaciones
        self._clock = clock

    async def handle(self, estudiante_id: str) -> list[MiPublicacionResponse]:
        """Ejecuta el caso de uso."""
        raise NotImplementedError
