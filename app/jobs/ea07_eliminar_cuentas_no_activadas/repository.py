"""EA-07 — Eliminar las cuentas no activadas. Implementación Mongo de lo que necesita el job."""
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.domain.contracts import IAccountRepository
from app.shared.domain.entities import EstadoCuenta


class MongoEliminarCuentasRepository(IAccountRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def eliminar_no_activadas(self, registradas_antes_de):
        # Índice ix_accounts_pending {status, createdAt}; el enlace va embebido y se elimina con la cuenta
        resultado = await self._db.accounts.delete_many(
            {"status": EstadoCuenta.PENDIENTE_ACTIVACION.value, "createdAt": {"$lte": registradas_antes_de}})
        return resultado.deleted_count
