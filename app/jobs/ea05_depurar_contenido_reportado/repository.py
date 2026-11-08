"""EA-05 — Eliminar contenido reportado vencido. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.domain.contracts import IReportRepository


class MongoDepurarReportesRepository(IReportRepository):
    """Implementa de IReportRepository: eliminar_vencidos."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def eliminar_vencidos(self, *args, **kwargs):
        raise NotImplementedError
