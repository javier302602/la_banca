"""CU-21 — Reaccionar a una publicación. Implementación Mongo (colección reactions).

Documento: {publicationId, userId, type, createdAt, publicationExpiresAt}. Índice único (publicationId, userId):
una reacción por estudiante. publicationExpiresAt alimenta el índice TTL, así se borran junto con la publicación.
El feed (CU-08) y el detalle (CU-09) reutilizan `resumen` para pintar los conteos.
"""
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.db.mongo import oid
from app.shared.domain.contracts import IReactionRepository
from app.shared.domain.entities import ResumenReacciones, TipoReaccion


class MongoReaccionesRepository(IReactionRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def guardar(self, publicacion_id, estudiante_id, tipo, publicacion_expira, ahora):
        await self._db.reactions.update_one(
            {"publicationId": oid(publicacion_id), "userId": oid(estudiante_id)},
            {"$set": {"type": tipo.value, "createdAt": ahora, "publicationExpiresAt": publicacion_expira}},
            upsert=True)

    async def quitar(self, publicacion_id, estudiante_id):
        await self._db.reactions.delete_one({"publicationId": oid(publicacion_id), "userId": oid(estudiante_id)})

    async def resumen(self, publicacion_ids, estudiante_id):
        claves = [c for c in (oid(i) for i in publicacion_ids) if c is not None]
        if not claves:
            return {}
        resultado: dict[str, ResumenReacciones] = {}
        conteos = self._db.reactions.aggregate([
            {"$match": {"publicationId": {"$in": claves}}},
            {"$group": {"_id": {"p": "$publicationId", "t": "$type"}, "n": {"$sum": 1}}},
        ])
        async for fila in await conteos:
            pid = str(fila["_id"]["p"])
            resultado.setdefault(pid, ResumenReacciones()).conteos[TipoReaccion(fila["_id"]["t"])] = fila["n"]
        async for mia in self._db.reactions.find({"publicationId": {"$in": claves}, "userId": oid(estudiante_id)}):
            resultado.setdefault(str(mia["publicationId"]), ResumenReacciones()).mia = TipoReaccion(mia["type"])
        return resultado
