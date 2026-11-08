"""CU-18 — Recuperar la contraseña. Implementación Mongo de lo que necesita el slice."""
from pymongo import ReturnDocument
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.db.mapeo import doc_a_estudiante, enlace_a_doc
from app.shared.db.mongo import oid
from app.shared.domain.contracts import IAccountRepository
from app.shared.domain.entities import EstadoCuenta, EstadoSesion


class MongoRecuperarContrasenaRepository(IAccountRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def buscar_por_correo(self, correo):
        doc = await self._db.accounts.find_one({"email": correo})
        return doc_a_estudiante(doc) if doc else None

    async def registrar_enlace(self, estudiante_id, proposito, enlace):
        await self._db.accounts.update_one({"_id": oid(estudiante_id)},
                                           {"$set": {"passwordReset": enlace_a_doc(enlace)}})

    async def restablecer_con_enlace(self, token_hash, password_hash, ahora):
        doc = await self._db.accounts.find_one_and_update(
            {"passwordReset.tokenHash": token_hash, "passwordReset.expiresAt": {"$gt": ahora},
             "status": EstadoCuenta.ACTIVA.value},
            {"$set": {"passwordHash": password_hash, "passwordReset.tokenHash": None,
                      "passwordReset.expiresAt": None}},
            return_document=ReturnDocument.AFTER)
        return doc_a_estudiante(doc) if doc else None

    async def cerrar_sesiones_de(self, estudiante_id, ahora):
        resultado = await self._db.sessions.update_many(
            {"userId": oid(estudiante_id), "status": EstadoSesion.ACTIVE.value},
            {"$set": {"status": EstadoSesion.CLOSED.value, "closedAt": ahora}})
        return resultado.modified_count
