"""CU-01 — Registrar cuenta. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.domain.contracts import IAccountRepository


class MongoRegistrarCuentaRepository(IAccountRepository):
    """Implementa de IAccountRepository: existe_por_correo, existe_por_nickname, crear, registrar_enlace."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def existe_por_correo(self, *args, **kwargs):
        raise NotImplementedError

    async def existe_por_nickname(self, *args, **kwargs):
        raise NotImplementedError

    async def crear(self, *args, **kwargs):
        raise NotImplementedError

    async def registrar_enlace(self, *args, **kwargs):
        raise NotImplementedError
