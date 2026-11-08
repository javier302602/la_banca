"""EA-05 — Eliminar contenido reportado vencido. Implementación Mongo de lo que necesita el job."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.domain.contracts import IReportRepository

LOTE = 500


class MongoDepurarReportesRepository(IReportRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def eliminar_vencidos(self, ahora):
        total, imagenes = 0, []
        while True:
            lote = [d async for d in self._db.reports.find(  # índice ix_reports_retention_end
                {"retentionEndsAt": {"$lte": ahora}}, {"reportedContentSnapshot.retainedImageKeys": 1}).limit(LOTE)]
            if not lote:
                return total, imagenes
            for d in lote:
                imagenes += (d.get("reportedContentSnapshot") or {}).get("retainedImageKeys") or []
            resultado = await self._db.reports.delete_many({"_id": {"$in": [d["_id"] for d in lote]}})
            total += resultado.deleted_count
