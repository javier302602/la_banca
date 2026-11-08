"""CU-14 — Reportar un chat. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING

from app.shared.db.mapeo import doc_a_chat, doc_a_mensaje, reporte_a_doc
from app.shared.db.mongo import oid
from app.shared.domain.contracts import IChatRepository, IReportRepository


class MongoChatLecturaRepository(IChatRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def buscar_por_id(self, chat_id):
        clave = oid(chat_id)
        doc = await self._db.chats.find_one({"_id": clave}) if clave else None
        return doc_a_chat(doc) if doc else None

    async def listar_mensajes(self, chat_id, despues_de=None):
        cursor = self._db.messages.find({"chatId": oid(chat_id)}).sort([("sentAt", ASCENDING), ("_id", ASCENDING)])
        return [doc_a_mensaje(d) async for d in cursor]


class MongoReportarChatRepository(IReportRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def crear(self, reporte):
        resultado = await self._db.reports.insert_one(reporte_a_doc(reporte))
        return str(resultado.inserted_id)
