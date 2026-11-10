"""EA-03 — Expirar chat por inactividad. Implementación Mongo de lo que necesita el job."""
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.domain.contracts import IChatRepository, IPublicationRepository
from app.shared.domain.entities import EstadoPublicacion

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


class MongoRetirarImagenesPublicacionesRepository(IPublicationRepository):
    """Vacía la lista de imágenes de las publicaciones vencidas o cerradas y devuelve sus claves."""

    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def retirar_imagenes_vencidas(self, ahora):
        filtro = {"images.0": {"$exists": True},
                  "$or": [{"expiresAt": {"$lte": ahora}}, {"status": {"$ne": EstadoPublicacion.ACTIVE.value}}]}
        claves: list[str] = []
        while True:
            lote = await self._db.publications.find(filtro, {"images.objectKey": 1}).limit(LOTE).to_list(LOTE)
            if not lote:
                return claves
            for doc in lote:
                # Se vacía solo si sigue con las mismas imágenes (otra ejecución simultánea no las duplica)
                r = await self._db.publications.update_one({"_id": doc["_id"], "images": {"$exists": True, "$ne": []}},
                                                           {"$set": {"images": []}})
                if r.modified_count:
                    claves += [i["objectKey"] for i in doc["images"]]
