"""Lectura de los datos públicos de las cuentas (SRS v2.0, cambio 2.1).

Compartido por los slices que pintan la foto o el avatar junto al nickname (feed, detalle, chat) y por
CU-20. La proyección deja fuera el correo, la contraseña y los enlaces: lo que no se lee no se puede
filtrar por error en una respuesta (RN-04).
"""
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.db.mapeo import doc_a_foto
from app.shared.db.mongo import COLACION_NICKNAME, oid
from app.shared.domain.contracts import IAccountRepository
from app.shared.domain.entities import EstadoCuenta, Estudiante

PROYECCION_PUBLICA = {"nickname": 1, "status": 1, "createdAt": 1, "activatedAt": 1, "bio": 1, "avatar": 1,
                      "photo": 1}


def doc_a_estudiante_publico(doc: dict) -> Estudiante:
    return Estudiante(id=str(doc["_id"]), correo_institucional="", password_hash="", nickname=doc["nickname"],
                      estado=EstadoCuenta(doc["status"]), fecha_registro=doc["createdAt"],
                      fecha_activacion=doc.get("activatedAt"), biografia=doc.get("bio") or "",
                      avatar=doc.get("avatar"), foto=doc_a_foto(doc.get("photo")))


class MongoPerfilesPublicosRepository(IAccountRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def buscar_varias(self, ids):
        claves = [c for c in (oid(i) for i in set(ids)) if c is not None]
        if not claves:
            return {}
        docs = await self._db.accounts.find({"_id": {"$in": claves}}, PROYECCION_PUBLICA).to_list(len(claves))
        return {str(d["_id"]): doc_a_estudiante_publico(d) for d in docs}

    async def buscar_activa_por_nickname(self, nickname):
        doc = await self._db.accounts.find_one({"nickname": nickname, "status": EstadoCuenta.ACTIVA.value},
                                               PROYECCION_PUBLICA, collation=COLACION_NICKNAME)
        return doc_a_estudiante_publico(doc) if doc else None
