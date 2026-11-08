"""CU-05 — Crear publicación. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.db.mapeo import publicacion_a_doc
from app.shared.db.mongo import oid
from app.shared.domain.contracts import IPublicationRepository
from app.shared.domain.entities import EstadoPublicacion


class MongoCrearPublicacionRepository(IPublicationRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def contar_activas_por_usuario(self, autor_id, ahora):
        # Índice ix_publications_author_act; vigencia evaluada al consultar (EA-02)
        return await self._db.publications.count_documents(
            {"authorId": oid(autor_id), "status": EstadoPublicacion.ACTIVE.value, "expiresAt": {"$gt": ahora}})

    async def crear(self, publicacion):
        resultado = await self._db.publications.insert_one(publicacion_a_doc(publicacion))
        return str(resultado.inserted_id)
