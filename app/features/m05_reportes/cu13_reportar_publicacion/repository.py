"""CU-13 — Reportar una publicación. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.domain.contracts import IPublicationRepository, IReportRepository


class MongoPublicacionLecturaRepository(IPublicationRepository):
    """Implementa de IPublicationRepository: buscar_por_id."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def buscar_por_id(self, *args, **kwargs):
        raise NotImplementedError


class MongoReportarPublicacionRepository(IReportRepository):
    """Implementa de IReportRepository: crear, retener_instantanea."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def crear(self, *args, **kwargs):
        raise NotImplementedError

    async def retener_instantanea(self, *args, **kwargs):
        raise NotImplementedError
