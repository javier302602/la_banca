"""CU-10 — Responder a una publicación. Implementación Mongo de lo que necesita el slice."""
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError

from app.shared.db.mapeo import chat_a_doc, doc_a_chat, doc_a_publicacion, mensaje_a_doc
from app.shared.db.mongo import en_transaccion, oid
from app.shared.domain.contracts import IChatRepository, IPublicationRepository
from app.shared.domain.errors import Conflicto


class MongoPublicacionLecturaRepository(IPublicationRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def buscar_por_id(self, publicacion_id):
        clave = oid(publicacion_id)
        doc = await self._db.publications.find_one({"_id": clave}) if clave else None
        return doc_a_publicacion(doc) if doc else None


class MongoResponderPublicacionRepository(IChatRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def buscar_por_usuario_y_publicacion(self, respondedor_id, publicacion_id):
        doc = await self._db.chats.find_one({"publicationId": oid(publicacion_id),
                                             "responderId": oid(respondedor_id)})
        return doc_a_chat(doc) if doc else None

    async def crear_con_primer_mensaje(self, chat, primer_mensaje):
        async def operacion(s):
            resultado = await self._db.chats.insert_one(chat_a_doc(chat), session=s)
            primer_mensaje.chat_id = str(resultado.inserted_id)
            await self._db.messages.insert_one(mensaje_a_doc(primer_mensaje), session=s)
            return str(resultado.inserted_id)

        try:
            return await en_transaccion(self._db, operacion)  # chat + primer mensaje atómicos
        except DuplicateKeyError:  # índice único uq_chats_pub_responder
            raise Conflicto("chat duplicado", codigo="chat_existente") from None

    async def eliminar_chat(self, chat_id):
        clave = oid(chat_id)

        async def operacion(s):
            imagenes = [d["imageAttachment"]["objectKey"] async for d in self._db.messages.find(
                {"chatId": clave, "imageAttachment": {"$ne": None}}, {"imageAttachment": 1}, session=s)]
            await self._db.messages.delete_many({"chatId": clave}, session=s)
            await self._db.chats.delete_one({"_id": clave}, session=s)
            return imagenes

        return await en_transaccion(self._db, operacion)
