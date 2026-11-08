"""CU-17 — Activar la cuenta. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.shared.db.mapeo import doc_a_estudiante, enlace_a_doc
from app.shared.db.mongo import oid
from app.shared.domain.contracts import IAccountRepository
from app.shared.domain.entities import EstadoCuenta, PropositoEnlace

CAMPO_ENLACE = {PropositoEnlace.ACTIVACION: "activation", PropositoEnlace.RECUPERACION: "passwordReset"}


class MongoActivarCuentaRepository(IAccountRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def activar_con_enlace(self, token_hash, ahora):
        # Una sola operación atómica: el token solo puede consumirse una vez (RNF-SEG-09)
        doc = await self._db.accounts.find_one_and_update(
            {"activation.tokenHash": token_hash, "activation.expiresAt": {"$gt": ahora},
             "status": EstadoCuenta.PENDIENTE_ACTIVACION.value},
            {"$set": {"status": EstadoCuenta.ACTIVA.value, "activatedAt": ahora,
                      "activation.tokenHash": None, "activation.expiresAt": None}},
            return_document=ReturnDocument.AFTER)
        return doc_a_estudiante(doc) if doc else None

    async def buscar_por_correo(self, correo):
        doc = await self._db.accounts.find_one({"email": correo})
        return doc_a_estudiante(doc) if doc else None

    async def registrar_enlace(self, estudiante_id, proposito, enlace):
        await self._db.accounts.update_one({"_id": oid(estudiante_id)},
                                           {"$set": {CAMPO_ENLACE[proposito]: enlace_a_doc(enlace)}})

    async def eliminar_no_activadas(self, registradas_antes_de):
        resultado = await self._db.accounts.delete_many(
            {"status": EstadoCuenta.PENDIENTE_ACTIVACION.value, "createdAt": {"$lte": registradas_antes_de}})
        return resultado.deleted_count
