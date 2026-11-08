"""CU-06 — Ver mis publicaciones activas. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.domain.contracts import IPublicationRepository


class MongoVerMisPublicacionesRepository(IPublicationRepository):
    """Implementa de IPublicationRepository: listar_activas_por_usuario."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def listar_activas_por_usuario(self, *args, **kwargs):
        raise NotImplementedError
