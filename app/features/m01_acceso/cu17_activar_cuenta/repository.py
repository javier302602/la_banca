"""CU-17 — Activar la cuenta. Implementación Mongo de lo que necesita el slice."""
from pymongo import ReturnDocument
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.db.mapeo import doc_a_estudiante, enlace_a_doc
from app.shared.db.mongo import oid
from app.shared.domain.contracts import IAccountRepository
from app.shared.domain.entities import MAX_INTENTOS_CODIGO, EstadoCuenta, PropositoEnlace

CAMPO_ENLACE = {PropositoEnlace.ACTIVACION: "activation", PropositoEnlace.RECUPERACION: "passwordReset"}


class MongoActivarCuentaRepository(IAccountRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def activar_con_codigo(self, estudiante_id, codigo_hash, ahora):
        # Una sola operación atómica: el código solo puede consumirse una vez y respeta el límite de intentos
        doc = await self._db.accounts.find_one_and_update(
            {"_id": oid(estudiante_id), "activation.tokenHash": codigo_hash, "activation.expiresAt": {"$gt": ahora},
             "activation.attempts": {"$not": {"$gte": MAX_INTENTOS_CODIGO}},
             "status": EstadoCuenta.PENDIENTE_ACTIVACION.value},
            {"$set": {"status": EstadoCuenta.ACTIVA.value, "activatedAt": ahora,
                      "activation.tokenHash": None, "activation.expiresAt": None}},
            return_document=ReturnDocument.AFTER)
        return doc_a_estudiante(doc) if doc else None

    async def sumar_intento_codigo(self, estudiante_id):
        doc = await self._db.accounts.find_one_and_update(
            {"_id": oid(estudiante_id)}, {"$inc": {"activation.attempts": 1}},
            projection={"activation.attempts": 1}, return_document=ReturnDocument.AFTER)
        return doc["activation"]["attempts"] if doc else MAX_INTENTOS_CODIGO

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
