"""EA-05 — Eliminar contenido reportado vencido. Automatismo (handler).

RF: RF-REP-08, RF-REP-09, RF-REP-11 · RNF-PRI-02
Elimina definitivamente cada Reporte con su ContenidoReportado cuando fecha_retencion_fin ≤ ahora,
junto con las imágenes copiadas al área de retención.
"""
import logging

from app.shared.domain.contracts import IClock, ImageStorage, IReportRepository

log = logging.getLogger("la_banca.ea05")


class DepurarContenidoReportadoHandler:
    def __init__(self, reportes: IReportRepository, imagenes: ImageStorage, clock: IClock) -> None:
        self._reportes = reportes
        self._imagenes = imagenes
        self._clock = clock

    async def handle(self) -> dict[str, int]:
        eliminados, referencias = await self._reportes.eliminar_vencidos(self._clock.ahora())
        borradas = 0
        for referencia in referencias:
            try:
                await self._imagenes.eliminar(referencia)
                borradas += 1
            except Exception:
                log.exception("No se pudo eliminar una imagen retenida")
        return {"reportes_eliminados": eliminados, "imagenes_eliminadas": borradas}
