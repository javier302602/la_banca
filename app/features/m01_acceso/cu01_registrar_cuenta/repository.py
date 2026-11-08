"""CU-01 — Registrar cuenta. Implementación Mongo de lo que necesita el slice."""
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError

from app.shared.db.mapeo import doc_a_estudiante, estudiante_a_doc
from app.shared.db.mongo import COLACION_NICKNAME, campo_duplicado, oid
from app.shared.domain.contracts import IAccountRepository
from app.shared.domain.entities import EstadoCuenta
from app.shared.domain.errors import Conflicto


class MongoRegistrarCuentaRepository(IAccountRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def buscar_por_correo(self, correo):
        doc = await self._db.accounts.find_one({"email": correo})
        return doc_a_estudiante(doc) if doc else None

    async def existe_por_nickname(self, nickname, excluir_id=None):
        filtro: dict = {"nickname": nickname}
        if excluir_id:
            filtro["_id"] = {"$ne": oid(excluir_id)}
        return await self._db.accounts.count_documents(filtro, collation=COLACION_NICKNAME, limit=1) > 0

    async def crear(self, estudiante):
        try:
            resultado = await self._db.accounts.insert_one(estudiante_a_doc(estudiante))
        except DuplicateKeyError as error:
            campo = campo_duplicado(error)
            raise Conflicto(f"{campo} duplicado", codigo=f"{campo}_duplicado") from None
        return str(resultado.inserted_id)

    async def eliminar_no_activadas(self, registradas_antes_de):
        resultado = await self._db.accounts.delete_many(
            {"status": EstadoCuenta.PENDIENTE_ACTIVACION.value, "createdAt": {"$lte": registradas_antes_de}})
        return resultado.deleted_count
