"""CU-08 — Consultar el feed «Ahora». Implementación Mongo de lo que necesita el slice.

Paginación por cursor (createdAt, _id) descendente: estable aunque entren publicaciones nuevas entre
bloques. Usa el índice ix_publications_feed {status, type, createdAt: -1, expiresAt}.
"""
import base64
import json
from datetime import datetime

from bson import ObjectId
from pymongo import DESCENDING
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.db.mapeo import doc_a_publicacion
from app.shared.db.mongo import oid
from app.shared.domain.contracts import IPublicationRepository
from app.shared.domain.entities import EstadoPublicacion
from app.shared.domain.errors import ErrorValidacion


def codificar_cursor(fecha: datetime, id_: ObjectId) -> str:
    crudo = json.dumps({"t": fecha.isoformat(), "id": str(id_)}).encode()
    return base64.urlsafe_b64encode(crudo).decode().rstrip("=")


def decodificar_cursor(cursor: str) -> tuple[datetime, ObjectId]:
    try:
        datos = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
        fecha, id_ = datetime.fromisoformat(datos["t"]), oid(datos["id"])
        if id_ is None:
            raise ValueError
        return fecha, id_
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise ErrorValidacion("El cursor del feed no es válido", codigo="cursor_invalido") from None


class MongoConsultarFeedRepository(IPublicationRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def listar_feed(self, ahora, tipo, cursor, limite):
        filtro: dict = {"status": EstadoPublicacion.ACTIVE.value, "expiresAt": {"$gt": ahora}}  # EA-02
        if tipo is not None:
            filtro["type"] = tipo.value
        if cursor:
            fecha, id_ = decodificar_cursor(cursor)
            filtro["$or"] = [{"createdAt": {"$lt": fecha}}, {"createdAt": fecha, "_id": {"$lt": id_}}]
        docs = await (self._db.publications.find(filtro)
                      .sort([("createdAt", DESCENDING), ("_id", DESCENDING)])
                      .limit(limite + 1).to_list(limite + 1))
        hay_mas = len(docs) > limite
        docs = docs[:limite]
        siguiente = codificar_cursor(docs[-1]["createdAt"], docs[-1]["_id"]) if hay_mas else None
        return [doc_a_publicacion(d) for d in docs], siguiente
