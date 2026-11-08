"""CU-05 — Crear publicación. Implementación Mongo de lo que necesita el slice."""
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.db.mapeo import publicacion_a_doc
from app.shared.db.mongo import en_transaccion, oid
from app.shared.domain.contracts import IPublicationRepository
from app.shared.domain.entities import EstadoPublicacion


class MongoCrearPublicacionRepository(IPublicationRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def contar_activas_por_usuario(self, autor_id, ahora):
        # Índice ix_publications_author_act; vigencia evaluada al consultar (EA-02)
        return await self._db.publications.count_documents(
            {"authorId": oid(autor_id), "status": EstadoPublicacion.ACTIVE.value, "expiresAt": {"$gt": ahora}})

    async def crear_si_hay_cupo(self, publicacion, maximo, ahora):
        autor = oid(publicacion.autor_id)

        async def operacion(s):
            # Escribir en la cuenta del autor hace que dos creaciones simultáneas choquen (WriteConflict →
            # TransientTransactionError); en_transaccion repite la perdedora, que ya ve la publicación nueva.
            await self._db.accounts.update_one({"_id": autor}, {"$inc": {"publicationsVersion": 1}}, session=s)
            activas = await self._db.publications.count_documents(
                {"authorId": autor, "status": EstadoPublicacion.ACTIVE.value, "expiresAt": {"$gt": ahora}}, session=s)
            if activas >= maximo:
                return None
            resultado = await self._db.publications.insert_one(publicacion_a_doc(publicacion), session=s)
            return str(resultado.inserted_id)

        return await en_transaccion(self._db, operacion)
