"""CU-03 — Cerrar sesión manualmente. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.domain.contracts import IAccountRepository


class MongoCerrarSesionRepository(IAccountRepository):
    """Implementa de IAccountRepository: cerrar_sesion."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def cerrar_sesion(self, *args, **kwargs):
        raise NotImplementedError
