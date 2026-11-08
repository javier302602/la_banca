"""CU-09 — Ver detalle de una publicación. Caso de uso (handler).

RF: RF-CHT-04, RF-FED-05, RF-FED-07, RF-FED-10, RF-FED-12
EA-02 también aplica: una publicación vencida o cerrada no se muestra como activa.

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from app.shared.domain.contracts import IClock, IPublicationRepository

from .request import DetallePublicacionResponse


class VerDetallePublicacionHandler:
    def __init__(self, publicaciones: IPublicationRepository, clock: IClock) -> None:
        self._publicaciones = publicaciones
        self._clock = clock

    async def handle(self, estudiante_id: str, publicacion_id: str) -> DetallePublicacionResponse:
        """Ejecuta el caso de uso."""
        raise NotImplementedError
