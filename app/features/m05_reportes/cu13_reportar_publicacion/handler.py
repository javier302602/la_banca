"""CU-13 — Reportar una publicación. Caso de uso (handler).

RF: RF-REP-01, RF-REP-03–08, RF-REP-10, RF-REP-12–15
Publicación activa de otro autor. Conserva una instantánea (ContenidoReportado) durante el plazo de retención configurado (inicial 7 días).

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from app.shared.domain.contracts import IClock, IConfigurationProvider, IPublicationRepository, IReportRepository

from .request import ReporteRequest, ReporteResponse


class ReportarPublicacionHandler:
    def __init__(self, publicaciones: IPublicationRepository, reportes: IReportRepository, config: IConfigurationProvider, clock: IClock) -> None:
        self._publicaciones = publicaciones
        self._reportes = reportes
        self._config = config
        self._clock = clock

    async def handle(self, estudiante_id: str, publicacion_id: str, body: ReporteRequest) -> ReporteResponse:
        """Ejecuta el caso de uso."""
        raise NotImplementedError
