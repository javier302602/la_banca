"""CU-06 — Ver mis publicaciones activas. Implementación Mongo de lo que necesita el slice."""
from pymongo import DESCENDING
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.db.mapeo import doc_a_publicacion
from app.shared.db.mongo import oid
from app.shared.domain.contracts import IPublicationRepository
from app.shared.domain.entities import EstadoPublicacion


class MongoVerMisPublicacionesRepository(IPublicationRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def listar_activas_por_usuario(self, autor_id, ahora):
        cursor = self._db.publications.find(
            {"authorId": oid(autor_id), "status": EstadoPublicacion.ACTIVE.value, "expiresAt": {"$gt": ahora}}
        ).sort([("createdAt", DESCENDING), ("_id", DESCENDING)])
        return [doc_a_publicacion(d) async for d in cursor]
