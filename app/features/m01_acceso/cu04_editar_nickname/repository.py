"""CU-04 — Editar nickname. Implementación Mongo de lo que necesita el slice."""
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError

from app.shared.db.mongo import COLACION_NICKNAME, en_transaccion, oid
from app.shared.domain.contracts import IAccountRepository
from app.shared.domain.errors import Conflicto


class MongoEditarNicknameRepository(IAccountRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def existe_por_nickname(self, nickname, excluir_id=None):
        filtro: dict = {"nickname": nickname}
        if excluir_id:
            filtro["_id"] = {"$ne": oid(excluir_id)}
        return await self._db.accounts.count_documents(filtro, collation=COLACION_NICKNAME, limit=1) > 0

    async def actualizar_nickname(self, estudiante_id, nickname):
        uid = oid(estudiante_id)

        async def operacion(s):
            await self._db.accounts.update_one({"_id": uid}, {"$set": {"nickname": nickname}}, session=s)
            # Copias desnormalizadas (RF-AUT-26)
            await self._db.publications.update_many({"authorId": uid}, {"$set": {"authorNickname": nickname}},
                                                    session=s)
            await self._db.chats.update_many({"authorId": uid}, {"$set": {"authorNickname": nickname}}, session=s)
            await self._db.chats.update_many({"responderId": uid}, {"$set": {"responderNickname": nickname}},
                                             session=s)
            await self._db.messages.update_many({"senderId": uid}, {"$set": {"senderNickname": nickname}},
                                                session=s)

        try:
            await en_transaccion(self._db, operacion)
        except DuplicateKeyError:
            raise Conflicto("nickname duplicado", codigo="nickname_duplicado") from None
