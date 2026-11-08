"""CU-05 — Crear publicación. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.domain.contracts import IPublicationRepository


class MongoCrearPublicacionRepository(IPublicationRepository):
    """Implementa de IPublicationRepository: contar_activas_por_usuario, crear."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def contar_activas_por_usuario(self, *args, **kwargs):
        raise NotImplementedError

    async def crear(self, *args, **kwargs):
        raise NotImplementedError
