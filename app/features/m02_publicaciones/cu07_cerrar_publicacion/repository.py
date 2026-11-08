"""CU-07 — Cerrar publicación manualmente. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.db.mapeo import doc_a_publicacion
from app.shared.db.mongo import oid
from app.shared.domain.contracts import IPublicationRepository
from app.shared.domain.entities import EstadoPublicacion


class MongoCerrarPublicacionRepository(IPublicationRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def buscar_por_id(self, publicacion_id):
        clave = oid(publicacion_id)
        doc = await self._db.publications.find_one({"_id": clave}) if clave else None
        return doc_a_publicacion(doc) if doc else None

    async def cerrar(self, publicacion_id, autor_id, ahora):
        # Condicional y atómico: solo si sigue activa, vigente y es del autor
        resultado = await self._db.publications.update_one(
            {"_id": oid(publicacion_id), "authorId": oid(autor_id), "status": EstadoPublicacion.ACTIVE.value,
             "expiresAt": {"$gt": ahora}},
            {"$set": {"status": EstadoPublicacion.CLOSED.value, "closedAt": ahora}})
        return resultado.modified_count == 1
