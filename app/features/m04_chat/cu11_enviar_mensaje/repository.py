"""CU-11 — Enviar mensaje en un chat. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.db.mapeo import doc_a_chat, mensaje_a_doc
from app.shared.db.mongo import en_transaccion, oid
from app.shared.domain.contracts import IChatRepository
from app.shared.domain.entities import EstadoChat


class MongoEnviarMensajeRepository(IChatRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def buscar_por_id(self, chat_id):
        clave = oid(chat_id)
        doc = await self._db.chats.find_one({"_id": clave}) if clave else None
        return doc_a_chat(doc) if doc else None

    async def agregar_mensaje(self, mensaje, nueva_expiracion):
        async def operacion(s):
            # Reinicia la expiración solo si el chat sigue vigente en este instante (RF-CHT-12/15)
            actualizado = await self._db.chats.update_one(
                {"_id": oid(mensaje.chat_id), "status": EstadoChat.ACTIVE.value,
                 "expiresAt": {"$gt": mensaje.fecha_envio}},
                {"$set": {"lastActivityAt": mensaje.fecha_envio, "expiresAt": nueva_expiracion,
                          f"lastReadAt.{mensaje.emisor_id}": mensaje.fecha_envio}},
                session=s)
            if actualizado.matched_count == 0:
                return None
            resultado = await self._db.messages.insert_one(mensaje_a_doc(mensaje), session=s)
            return str(resultado.inserted_id)

        return await en_transaccion(self._db, operacion)
