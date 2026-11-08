"""CU-12 — Ver mis chats activos y abrir uno. Implementación Mongo de lo que necesita el slice."""
from pymongo import ASCENDING, DESCENDING
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.db.mapeo import doc_a_chat, doc_a_mensaje
from app.shared.db.mongo import oid
from app.shared.domain.contracts import IChatRepository
from app.shared.domain.entities import EstadoChat


class MongoVerMisChatsRepository(IChatRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def listar_activos_por_usuario(self, usuario_id, ahora):
        cursor = self._db.chats.find(
            {"participants": oid(usuario_id), "status": EstadoChat.ACTIVE.value, "expiresAt": {"$gt": ahora}}
        ).sort("lastActivityAt", DESCENDING)
        return [doc_a_chat(d) async for d in cursor]

    async def buscar_por_id(self, chat_id):
        clave = oid(chat_id)
        doc = await self._db.chats.find_one({"_id": clave}) if clave else None
        return doc_a_chat(doc) if doc else None

    async def listar_mensajes(self, chat_id, despues_de=None):
        filtro: dict = {"chatId": oid(chat_id)}
        if despues_de is not None:
            filtro["sentAt"] = {"$gt": despues_de}
        cursor = self._db.messages.find(filtro).sort([("sentAt", ASCENDING), ("_id", ASCENDING)])
        return [doc_a_mensaje(d) async for d in cursor]

    async def buscar_mensaje(self, chat_id, mensaje_id):
        clave = oid(mensaje_id)
        doc = await self._db.messages.find_one({"_id": clave, "chatId": oid(chat_id)}) if clave else None
        return doc_a_mensaje(doc) if doc else None

    async def marcar_leido(self, chat_id, usuario_id, ahora):
        await self._db.chats.update_one({"_id": oid(chat_id)}, {"$set": {f"lastReadAt.{usuario_id}": ahora}})
