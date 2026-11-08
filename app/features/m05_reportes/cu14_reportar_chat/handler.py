"""CU-14 — Reportar un chat. Caso de uso (handler).

RF: RF-REP-02–05, RF-REP-07, RF-REP-08, RF-REP-10, RF-REP-14–17
Solo un participante de un chat activo. La instantánea incluye mensajes e imágenes y suspende la limpieza física del chat (EA-03) mientras dure la retención.

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from app.shared.domain.contracts import IChatRepository, IClock, IConfigurationProvider, IReportRepository, ImageStorage

from .request import ReporteRequest, ReporteResponse


class ReportarChatHandler:
    def __init__(self, chats: IChatRepository, reportes: IReportRepository, imagenes: ImageStorage, config: IConfigurationProvider, clock: IClock) -> None:
        self._chats = chats
        self._reportes = reportes
        self._imagenes = imagenes
        self._config = config
        self._clock = clock

    async def handle(self, estudiante_id: str, chat_id: str, body: ReporteRequest) -> ReporteResponse:
        """Ejecuta el caso de uso."""
        raise NotImplementedError
