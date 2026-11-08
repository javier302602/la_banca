"""CU-18 — Recuperar la contraseña. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.domain.contracts import IAccountRepository


class MongoRecuperarContrasenaRepository(IAccountRepository):
    """Implementa de IAccountRepository: buscar_por_correo, registrar_enlace, consumir_enlace, actualizar_contrasena, cerrar_sesiones_de."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def buscar_por_correo(self, *args, **kwargs):
        raise NotImplementedError

    async def registrar_enlace(self, *args, **kwargs):
        raise NotImplementedError

    async def consumir_enlace(self, *args, **kwargs):
        raise NotImplementedError

    async def actualizar_contrasena(self, *args, **kwargs):
        raise NotImplementedError

    async def cerrar_sesiones_de(self, *args, **kwargs):
        raise NotImplementedError
