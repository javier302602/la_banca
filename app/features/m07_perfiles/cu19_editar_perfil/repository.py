"""CU-19 — Editar mi perfil. Implementación Mongo de lo que necesita el slice."""
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.db.mapeo import foto_a_doc
from app.shared.db.mongo import oid
from app.shared.db.perfiles import PROYECCION_PUBLICA, doc_a_estudiante_publico
from app.shared.domain.contracts import IAccountRepository


class MongoEditarPerfilRepository(IAccountRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def buscar_por_id(self, estudiante_id):
        clave = oid(estudiante_id)
        doc = await self._db.accounts.find_one({"_id": clave}, PROYECCION_PUBLICA) if clave else None
        return doc_a_estudiante_publico(doc) if doc else None

    async def actualizar_perfil(self, estudiante_id, biografia, avatar):
        await self._db.accounts.update_one({"_id": oid(estudiante_id)}, {"$set": {"bio": biografia, "avatar": avatar}})

    async def actualizar_foto(self, estudiante_id, foto):
        await self._db.accounts.update_one({"_id": oid(estudiante_id)}, {"$set": {"photo": foto_a_doc(foto)}})
