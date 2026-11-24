"""CU-22 — Compartir ubicación. Implementación Mongo (colección live_locations).

Un documento por (chatId, userId) con la última posición; se reemplaza en cada envío (no hay historial).
El índice TTL sobre expiresAt la borra si deja de actualizarse. Guardarla en Mongo, y no en memoria, permite que
los dos participantes estén conectados a procesos distintos del servidor (gunicorn con varios workers).
"""
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.db.mapeo import doc_a_chat
from app.shared.db.mongo import oid
from app.shared.domain.contracts import IChatRepository, IUbicacionRepository
from app.shared.domain.entities import UbicacionEnVivo


class MongoChatUbicacionRepository(IChatRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def buscar_por_id(self, chat_id):
        clave = oid(chat_id)
        doc = await self._db.chats.find_one({"_id": clave}) if clave else None
        return doc_a_chat(doc) if doc else None


class MongoUbicacionRepository(IUbicacionRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def guardar(self, u):
        await self._db.live_locations.replace_one(
            {"chatId": oid(u.chat_id), "userId": oid(u.estudiante_id)},
            {"chatId": oid(u.chat_id), "userId": oid(u.estudiante_id), "nickname": u.nickname, "lat": u.lat,
             "lng": u.lng, "accuracy": u.precision, "updatedAt": u.actualizado, "expiresAt": u.expira_en},
            upsert=True)

    async def buscar(self, chat_id, estudiante_id):
        d = await self._db.live_locations.find_one({"chatId": oid(chat_id), "userId": oid(estudiante_id)})
        if d is None:
            return None
        return UbicacionEnVivo(chat_id=str(d["chatId"]), estudiante_id=str(d["userId"]), nickname=d["nickname"],
                               lat=d["lat"], lng=d["lng"], precision=d["accuracy"], actualizado=d["updatedAt"],
                               expira_en=d["expiresAt"])

    async def borrar(self, chat_id, estudiante_id):
        await self._db.live_locations.delete_one({"chatId": oid(chat_id), "userId": oid(estudiante_id)})
