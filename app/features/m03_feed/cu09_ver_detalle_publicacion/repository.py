"""CU-09 — Ver detalle de una publicación. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.domain.contracts import IPublicationRepository


class MongoVerDetallePublicacionRepository(IPublicationRepository):
    """Implementa de IPublicationRepository: buscar_por_id."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def buscar_por_id(self, *args, **kwargs):
        raise NotImplementedError
