"""CU-03 — Cerrar sesión manualmente. Implementación Mongo de lo que necesita el slice."""
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.db.mapeo import doc_a_sesion
from app.shared.db.mongo import oid
from app.shared.domain.contracts import IAccountRepository
from app.shared.domain.entities import EstadoSesion


class MongoCerrarSesionRepository(IAccountRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def buscar_sesion_por_token(self, token_hash):
        doc = await self._db.sessions.find_one({"tokenHash": token_hash})
        return doc_a_sesion(doc) if doc else None

    async def finalizar_sesion(self, sesion_id, estado, ahora):
        await self._db.sessions.update_one({"_id": oid(sesion_id), "status": EstadoSesion.ACTIVE.value},
                                           {"$set": {"status": estado.value, "closedAt": ahora}})
