"""CU-15 — Configurar los parámetros del sistema. Implementación Mongo (colección system_parameters)."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.db.mapeo import parametro_a_doc
from app.shared.domain.contracts import IParameterRepository


class MongoParameterRepository(IParameterRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def guardar(self, parametro):
        doc = parametro_a_doc(parametro)
        await self._db.system_parameters.replace_one({"_id": doc["_id"]}, doc, upsert=True)
