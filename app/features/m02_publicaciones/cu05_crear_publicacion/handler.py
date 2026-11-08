"""CU-05 — Crear publicación. Caso de uso (handler).

RF: RF-PUB-01–07, RF-PUB-12–16
Duración fija de 24 h (DURACION_PUBLICACION). Máximo de activas por autor desde CFG (inicial 3).

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from app.shared.domain.contracts import IClock, IConfigurationProvider, IPublicationRepository

from .request import CrearPublicacionRequest, PublicacionResponse


class CrearPublicacionHandler:
    def __init__(self, publicaciones: IPublicationRepository, config: IConfigurationProvider, clock: IClock) -> None:
        self._publicaciones = publicaciones
        self._config = config
        self._clock = clock

    async def handle(self, estudiante_id: str, body: CrearPublicacionRequest) -> PublicacionResponse:
        """Ejecuta el caso de uso."""
        raise NotImplementedError
