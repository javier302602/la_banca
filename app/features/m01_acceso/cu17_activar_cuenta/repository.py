"""CU-17 — Activar la cuenta. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.domain.contracts import IAccountRepository


class MongoActivarCuentaRepository(IAccountRepository):
    """Implementa de IAccountRepository: consumir_enlace, activar, buscar_por_correo, registrar_enlace."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def consumir_enlace(self, *args, **kwargs):
        raise NotImplementedError

    async def activar(self, *args, **kwargs):
        raise NotImplementedError

    async def buscar_por_correo(self, *args, **kwargs):
        raise NotImplementedError

    async def registrar_enlace(self, *args, **kwargs):
        raise NotImplementedError
