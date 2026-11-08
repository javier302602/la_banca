"""CU-07 — Cerrar publicación manualmente. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.domain.contracts import IPublicationRepository


class MongoCerrarPublicacionRepository(IPublicationRepository):
    """Implementa de IPublicationRepository: buscar_por_id, cerrar."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def buscar_por_id(self, *args, **kwargs):
        raise NotImplementedError

    async def cerrar(self, *args, **kwargs):
        raise NotImplementedError
