"""EA-05 — Eliminar contenido reportado vencido. Automatismo (handler).

RF: RF-REP-08, RF-REP-09, RF-REP-11
Elimina definitivamente Reporte y ContenidoReportado (textos e imágenes) con fecha_retencion_fin ≤ ahora.

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from app.shared.domain.contracts import IClock, IReportRepository, ImageStorage


class DepurarContenidoReportadoHandler:
    def __init__(self, reportes: IReportRepository, imagenes: ImageStorage, clock: IClock) -> None:
        self._reportes = reportes
        self._imagenes = imagenes
        self._clock = clock

    async def handle(self) -> int:
        """Ejecuta la limpieza y devuelve la cantidad depurada."""
        raise NotImplementedError
