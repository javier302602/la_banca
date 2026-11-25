"""EA-05 — Eliminar contenido reportado vencido. Implementación Mongo de lo que necesita el job.

Fase 5: solo se borran los reportes ya revisados (RESUELTO o DESCARTADO) cuyo plazo de retención venció. Un
reporte PENDIENTE se conserva hasta que un administrador lo revise, para no perder la evidencia.
"""
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.domain.contracts import IReportRepository
from app.shared.domain.entities import EstadoReporte

LOTE = 500
REVISADOS = [EstadoReporte.RESUELTO.value, EstadoReporte.DESCARTADO.value]


class MongoDepurarReportesRepository(IReportRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def eliminar_vencidos(self, ahora):
        total, imagenes = 0, []
        while True:
            lote = [d async for d in self._db.reports.find(  # índice ix_reports_retention_end
                {"retentionEndsAt": {"$lte": ahora}, "status": {"$in": REVISADOS}},
                {"reportedContentSnapshot.retainedImageKeys": 1}).limit(LOTE)]
            if not lote:
                return total, imagenes
            for d in lote:
                imagenes += (d.get("reportedContentSnapshot") or {}).get("retainedImageKeys") or []
            resultado = await self._db.reports.delete_many({"_id": {"$in": [d["_id"] for d in lote]}})
            total += resultado.deleted_count
