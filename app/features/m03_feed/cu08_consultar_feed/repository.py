"""CU-08 — Consultar el feed «Ahora». Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.domain.contracts import IPublicationRepository


class MongoConsultarFeedRepository(IPublicationRepository):
    """Implementa de IPublicationRepository: listar_feed."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def listar_feed(self, *args, **kwargs):
        raise NotImplementedError
