"""CU-14 — Reportar un chat. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.domain.contracts import IChatRepository, IReportRepository


class MongoChatLecturaRepository(IChatRepository):
    """Implementa de IChatRepository: buscar_por_id, listar_mensajes."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def buscar_por_id(self, *args, **kwargs):
        raise NotImplementedError

    async def listar_mensajes(self, *args, **kwargs):
        raise NotImplementedError


class MongoReportarChatRepository(IReportRepository):
    """Implementa de IReportRepository: crear, retener_instantanea."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def crear(self, *args, **kwargs):
        raise NotImplementedError

    async def retener_instantanea(self, *args, **kwargs):
        raise NotImplementedError
