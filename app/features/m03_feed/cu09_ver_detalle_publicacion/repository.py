"""CU-09 — Ver detalle de una publicación. Implementación Mongo de lo que necesita el slice."""
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.db.mapeo import doc_a_chat, doc_a_publicacion
from app.shared.db.mongo import oid
from app.shared.domain.contracts import IChatRepository, IPublicationRepository


class MongoVerDetallePublicacionRepository(IPublicationRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def buscar_por_id(self, publicacion_id):
        clave = oid(publicacion_id)
        doc = await self._db.publications.find_one({"_id": clave}) if clave else None
        return doc_a_publicacion(doc) if doc else None


class MongoChatExistenteRepository(IChatRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def buscar_por_usuario_y_publicacion(self, respondedor_id, publicacion_id):
        doc = await self._db.chats.find_one({"publicationId": oid(publicacion_id),
                                             "responderId": oid(respondedor_id)})
        return doc_a_chat(doc) if doc else None
