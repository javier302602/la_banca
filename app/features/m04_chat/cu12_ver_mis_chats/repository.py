"""CU-12 — Ver mis chats activos y abrir uno. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.domain.contracts import IChatRepository


class MongoVerMisChatsRepository(IChatRepository):
    """Implementa de IChatRepository: listar_activos_por_usuario, buscar_por_id, listar_mensajes."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def listar_activos_por_usuario(self, *args, **kwargs):
        raise NotImplementedError

    async def buscar_por_id(self, *args, **kwargs):
        raise NotImplementedError

    async def listar_mensajes(self, *args, **kwargs):
        raise NotImplementedError
