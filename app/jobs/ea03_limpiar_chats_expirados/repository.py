"""EA-03 — Expirar chat por inactividad. Implementación Mongo de lo que necesita el job."""
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.domain.contracts import IChatRepository

LOTE = 500


class MongoLimpiarChatsRepository(IChatRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def eliminar_expirados(self, ahora):
        total, imagenes = 0, []
        while True:
            ids = [d["_id"] async for d in self._db.chats.find({"expiresAt": {"$lte": ahora}}, {"_id": 1}).limit(LOTE)]
            if not ids:
                return total, imagenes
            async for m in self._db.messages.find({"chatId": {"$in": ids}, "imageAttachment": {"$ne": None}},
                                                  {"imageAttachment.objectKey": 1}):
                imagenes.append(m["imageAttachment"]["objectKey"])
            await self._db.messages.delete_many({"chatId": {"$in": ids}})
            resultado = await self._db.chats.delete_many({"_id": {"$in": ids}, "expiresAt": {"$lte": ahora}})
            total += resultado.deleted_count
