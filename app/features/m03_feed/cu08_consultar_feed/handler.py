"""CU-08 — Consultar el feed «Ahora». Caso de uso (handler).

RF: RF-FED-01–04, RF-FED-06–09, RF-FED-11–13, RF-FED-15–19
EA-02 (Expirar publicación; RF-PUB-09, RF-FED-02, RF-CHT-06, RF-CHT-17) se evalúa en la consulta: solo fecha_expiracion > ahora. Filtro opcional por tipo y paginado por bloques de 20 (cursor). Las publicaciones propias se marcan «Tu publicación».

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from app.shared.domain.contracts import IClock, IPublicationRepository

from .request import ConsultarFeedRequest, FeedResponse


class ConsultarFeedHandler:
    def __init__(self, publicaciones: IPublicationRepository, clock: IClock) -> None:
        self._publicaciones = publicaciones
        self._clock = clock

    async def handle(self, estudiante_id: str, body: ConsultarFeedRequest) -> FeedResponse:
        """Ejecuta el caso de uso."""
        raise NotImplementedError
