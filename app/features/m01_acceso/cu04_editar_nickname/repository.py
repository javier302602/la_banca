"""CU-04 — Editar nickname. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.domain.contracts import IAccountRepository


class MongoEditarNicknameRepository(IAccountRepository):
    """Implementa de IAccountRepository: existe_por_nickname, actualizar_nickname."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def existe_por_nickname(self, *args, **kwargs):
        raise NotImplementedError

    async def actualizar_nickname(self, *args, **kwargs):
        raise NotImplementedError
