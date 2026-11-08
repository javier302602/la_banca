"""EA-07 — Eliminar las cuentas no activadas. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.domain.contracts import IAccountRepository


class MongoEliminarCuentasRepository(IAccountRepository):
    """Implementa de IAccountRepository: eliminar_no_activadas."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def eliminar_no_activadas(self, *args, **kwargs):
        raise NotImplementedError
