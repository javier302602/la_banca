"""Cliente Motor compartido, helpers de mapeo y creación de colecciones/índices del Entregable 2 (Anexo B).

Las operaciones atómicas de varios documentos usan transacciones: MongoDB debe ser un replica set
(MongoDB Atlas lo es; en local: `mongod --replSet rs0` o la imagen de Docker con replica set).
"""
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorClientSession, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pymongo.collation import Collation
from pymongo.errors import CollectionInvalid, PyMongoError

from app.shared.config.provider import variable

log = logging.getLogger("la_banca.db")

# Colación sin distinción de mayúsculas para el nickname (RN-05 / RN-33)
COLACION_NICKNAME = Collation(locale="en", strength=2)

_client: AsyncIOMotorClient | None = None
_indices_creados = False
T = TypeVar("T")


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        uri = variable("MONGO_URI")
        if not uri:
            raise RuntimeError("Falta configurar MONGO_URI")
        _client = AsyncIOMotorClient(uri, tz_aware=True, serverSelectionTimeoutMS=5000)
    return _client


def get_database() -> AsyncIOMotorDatabase:
    """Dependencia FastAPI que entrega la base configurada (Entregable 2: la_banca_db)."""
    return get_client()[variable("MONGO_DB", "la_banca_db")]


def oid(valor: str | None) -> ObjectId | None:
    """Convierte un id de la API en ObjectId; None si no es válido (se trata como no encontrado)."""
    try:
        return ObjectId(valor) if valor else None
    except (InvalidId, TypeError):
        return None


async def en_transaccion(db: AsyncIOMotorDatabase,
                         operacion: Callable[[AsyncIOMotorClientSession], Awaitable[T]]) -> T:
    """Ejecuta `operacion(sesion)` dentro de una transacción con reintentos (RNF-FIA-03)."""
    async with await db.client.start_session() as sesion:
        return await sesion.with_transaction(operacion)


# --- Esquema físico (Entregable 2, Anexo B) ------------------------------------
def _validador_accounts(dominio: str | None) -> dict:
    patron_email = (f"^[a-z0-9._%+-]+@{re.escape(dominio.lower())}$" if dominio else "^[^@\\s]+@[^@\\s]+$")
    enlace = lambda minimo: {  # noqa: E731
        "bsonType": "object",
        "properties": {
            "tokenHash": {"bsonType": ["string", "null"]},
            "expiresAt": {"bsonType": ["date", "null"]},
            "sentCount": {"bsonType": "int", "minimum": minimo, "maximum": 5},
        },
    }
    return {"$jsonSchema": {
        "bsonType": "object",
        "required": ["email", "passwordHash", "nickname", "status", "createdAt"],
        "properties": {
            "email": {"bsonType": "string", "pattern": patron_email},
            "passwordHash": {"bsonType": "string", "minLength": 60},
            "nickname": {"bsonType": "string", "pattern": "^[a-zA-Z0-9_]{3,20}$"},
            "status": {"enum": ["PENDIENTE_ACTIVACION", "ACTIVA"]},
            "activation": enlace(1),
            "passwordReset": enlace(0),
            "createdAt": {"bsonType": "date"},
            "activatedAt": {"bsonType": ["date", "null"]},
        },
    }}


VALIDADOR_LOGIN_ATTEMPTS = {"$jsonSchema": {
    "bsonType": "object",
    "required": ["email", "failedCount", "firstFailedAt", "lastFailedAt"],
    "properties": {
        "email": {"bsonType": "string"},
        "failedCount": {"bsonType": "int", "minimum": 1, "maximum": 5},
        "firstFailedAt": {"bsonType": "date"},
        "lastFailedAt": {"bsonType": "date"},
        "lockedUntil": {"bsonType": ["date", "null"]},
    },
}}

COLECCIONES = ["accounts", "login_attempts", "sessions", "publications", "chats", "messages",
               "reports", "system_parameters"]


async def _asegurar_coleccion(db: AsyncIOMotorDatabase, nombre: str, validador: dict | None) -> None:
    opciones: dict[str, Any] = {}
    if validador:
        # "moderate": las cuentas creadas con un dominio anterior siguen siendo editables (RF-CFG-12)
        opciones = {"validator": validador, "validationLevel": "moderate"}
    try:
        await db.create_collection(nombre, **opciones)
    except CollectionInvalid:
        if validador:
            await db.command("collMod", nombre, **opciones)


async def crear_indices(db: AsyncIOMotorDatabase, dominio: str | None) -> None:
    """Crea colecciones, validadores $jsonSchema e índices. Idempotente."""
    validadores = {"accounts": _validador_accounts(dominio), "login_attempts": VALIDADOR_LOGIN_ATTEMPTS}
    for nombre in COLECCIONES:
        await _asegurar_coleccion(db, nombre, validadores.get(nombre))

    await db.accounts.create_index([("email", ASCENDING)], unique=True, name="uq_accounts_email")
    await db.accounts.create_index([("nickname", ASCENDING)], unique=True, name="uq_accounts_nickname",
                                   collation=COLACION_NICKNAME)
    await db.accounts.create_index([("activation.expiresAt", ASCENDING)], name="ix_accounts_activation_exp")
    await db.accounts.create_index([("activation.tokenHash", ASCENDING)], name="ix_accounts_activation_token",
                                   sparse=True)
    await db.accounts.create_index([("passwordReset.tokenHash", ASCENDING)], name="ix_accounts_reset_token",
                                   sparse=True)
    await db.accounts.create_index([("status", ASCENDING), ("createdAt", ASCENDING)], name="ix_accounts_pending")

    await db.login_attempts.create_index([("email", ASCENDING)], unique=True, name="uq_login_attempts_email")
    await db.login_attempts.create_index([("lockedUntil", ASCENDING)], expireAfterSeconds=0,
                                         name="ttl_login_attempts_locked")
    await db.login_attempts.create_index([("lastFailedAt", ASCENDING)], expireAfterSeconds=900,
                                         name="ttl_login_attempts_cleanup")

    await db.sessions.create_index([("tokenHash", ASCENDING)], unique=True, name="uq_sessions_token")
    await db.sessions.create_index([("userId", ASCENDING), ("status", ASCENDING)], name="ix_sessions_user_status")
    await db.sessions.create_index([("expiresAt", ASCENDING)], name="ix_sessions_exp")

    await db.publications.create_index([("status", ASCENDING), ("type", ASCENDING), ("createdAt", DESCENDING),
                                        ("expiresAt", ASCENDING)], name="ix_publications_feed")
    await db.publications.create_index([("authorId", ASCENDING), ("status", ASCENDING), ("expiresAt", ASCENDING)],
                                       name="ix_publications_author_act")

    await db.chats.create_index([("publicationId", ASCENDING), ("responderId", ASCENDING)], unique=True,
                                name="uq_chats_pub_responder")
    await db.chats.create_index([("participants", ASCENDING), ("status", ASCENDING), ("expiresAt", DESCENDING)],
                                name="ix_chats_participants_exp")

    await db.messages.create_index([("chatId", ASCENDING), ("sentAt", ASCENDING)], name="ix_messages_chat_sent")

    await db.reports.create_index([("retentionEndsAt", ASCENDING)], name="ix_reports_retention_end")
    await db.reports.create_index([("targetType", ASCENDING), ("targetId", ASCENDING)], name="ix_reports_target")


async def asegurar_indices_una_vez() -> None:
    """Se invoca al arrancar la app; un fallo se registra sin impedir el arranque."""
    global _indices_creados
    if _indices_creados:
        return
    from app.shared.config.provider import get_config
    from app.shared.domain.entities import ClaveParametro

    try:
        try:
            dominio = get_config().texto(ClaveParametro.DOMINIO_INSTITUCIONAL)
        except RuntimeError:
            dominio = None
        await crear_indices(get_database(), dominio)
        _indices_creados = True
    except (PyMongoError, RuntimeError) as error:
        log.error("No se pudieron crear los índices de MongoDB: %s", error)
