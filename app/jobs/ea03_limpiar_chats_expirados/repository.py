"""EA-03 — Expirar chat por inactividad (limpieza física). Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.domain.contracts import IChatRepository


class MongoLimpiarChatsRepository(IChatRepository):
    """Implementa de IChatRepository: eliminar_expirados."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def eliminar_expirados(self, *args, **kwargs):
        raise NotImplementedError
