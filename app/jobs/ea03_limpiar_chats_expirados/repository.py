"""EA-03 — Expirar chat por inactividad. Implementación Mongo de lo que necesita el job."""
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.domain.contracts import IChatRepository, IPublicationRepository
from app.shared.domain.entities import RETENCION_ARCHIVOS_PUBLICACION

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
            async for m in self._db.messages.find(
                    {"chatId": {"$in": ids},
                     "$or": [{"imageAttachment": {"$ne": None}}, {"documentAttachment": {"$nin": [None]}}]},
                    {"imageAttachment.objectKey": 1, "documentAttachment.objectKey": 1}):
                for campo in ("imageAttachment", "documentAttachment"):  # SRS v2.0: también documentos
                    if m.get(campo):
                        imagenes.append(m[campo]["objectKey"])
            await self._db.messages.delete_many({"chatId": {"$in": ids}})
            resultado = await self._db.chats.delete_many({"_id": {"$in": ids}, "expiresAt": {"$lte": ahora}})
            total += resultado.deleted_count


class MongoRetirarImagenesPublicacionesRepository(IPublicationRepository):
    """Retira imágenes y video de las publicaciones que vencieron hace 29 días (un día antes de que el índice
    TTL borre el documento), para que los admins puedan revisarlas mientras tanto. Devuelve las claves."""

    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def retirar_imagenes_vencidas(self, ahora):
        filtro = {"expiresAt": {"$lte": ahora - RETENCION_ARCHIVOS_PUBLICACION},
                  "$or": [{"images.0": {"$exists": True}}, {"video": {"$ne": None}}]}
        claves: list[str] = []
        while True:
            lote = await (self._db.publications.find(filtro, {"images.objectKey": 1, "video.objectKey": 1})
                          .limit(LOTE).to_list(LOTE))
            if not lote:
                return claves
            for doc in lote:
                # Se vacía solo si sigue con archivos (otra ejecución simultánea no los duplica)
                r = await self._db.publications.update_one({"_id": doc["_id"], "$or": filtro["$or"]},
                                                           {"$set": {"images": [], "video": None}})
                if r.modified_count:
                    claves += [i["objectKey"] for i in doc.get("images") or []]
                    if doc.get("video"):
                        claves.append(doc["video"]["objectKey"])
