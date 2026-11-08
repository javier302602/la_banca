"""CU-11 — Enviar mensaje en un chat. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.domain.contracts import IChatRepository


class MongoEnviarMensajeRepository(IChatRepository):
    """Implementa de IChatRepository: buscar_por_id, agregar_mensaje."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def buscar_por_id(self, *args, **kwargs):
        raise NotImplementedError

    async def agregar_mensaje(self, *args, **kwargs):
        raise NotImplementedError
