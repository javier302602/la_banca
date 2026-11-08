"""CU-02 — Iniciar sesión. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.domain.contracts import IAccountRepository


class MongoIniciarSesionRepository(IAccountRepository):
    """Implementa de IAccountRepository: obtener_intento, registrar_intento_fallido, reiniciar_intentos, buscar_por_correo, crear_sesion."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def obtener_intento(self, *args, **kwargs):
        raise NotImplementedError

    async def registrar_intento_fallido(self, *args, **kwargs):
        raise NotImplementedError

    async def reiniciar_intentos(self, *args, **kwargs):
        raise NotImplementedError

    async def buscar_por_correo(self, *args, **kwargs):
        raise NotImplementedError

    async def crear_sesion(self, *args, **kwargs):
        raise NotImplementedError
