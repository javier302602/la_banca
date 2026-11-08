"""Cliente Motor compartido, helpers de mapeo y creación de colecciones/índices del Entregable 2 (Anexo B).

Las operaciones atómicas de varios documentos usan transacciones: MongoDB debe ser un replica set
(MongoDB Atlas lo es; en local: `mongod --replSet rs0` o la imagen de Docker con replica set).
"""
import asyncio
import logging
import random
import re
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorClientSession, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pymongo.collation import Collation
from pymongo.errors import CollectionInvalid, DuplicateKeyError, PyMongoError

from app.shared.config.provider import variable

log = logging.getLogger("la_banca.db")

# Colación sin distinción de mayúsculas para el nickname (RN-05 / RN-33)
COLACION_NICKNAME = Collation(locale="en", strength=2)

# Un cliente por event loop: Motor queda ligado al loop en que se usa por primera vez y algunos
# entornos (pruebas, runtimes serverless) crean más de un loop en el mismo proceso.
_clientes: dict[asyncio.AbstractEventLoop, AsyncIOMotorClient] = {}
_indices_creados = False
T = TypeVar("T")


def get_client() -> AsyncIOMotorClient:
    loop = asyncio.get_running_loop()
    cliente = _clientes.get(loop)
    if cliente is None:
        uri = variable("MONGO_URI")
        if not uri:
            raise RuntimeError("Falta configurar MONGO_URI")
        for viejo in [l for l in _clientes if l.is_closed()]:
            _clientes.pop(viejo).close()
        cliente = _clientes[loop] = AsyncIOMotorClient(uri, tz_aware=True, serverSelectionTimeoutMS=5000)
    return cliente


def base_de_datos() -> AsyncIOMotorDatabase:
    """Base configurada (Entregable 2: la_banca_db). Debe llamarse dentro de un event loop."""
    return get_client()[variable("MONGO_DB", "la_banca_db")]


async def get_database() -> AsyncIOMotorDatabase:
    """Dependencia FastAPI (async: se resuelve en el event loop de la solicitud)."""
    return base_de_datos()


def oid(valor: str | None) -> ObjectId | None:
    """Convierte un id de la API en ObjectId; None si no es válido (se trata como no encontrado)."""
    try:
        return ObjectId(valor) if valor else None
    except (InvalidId, TypeError):
        return None


def campo_duplicado(error: DuplicateKeyError) -> str:
    """Nombre del campo que violó un índice único ('email', 'nickname', …)."""
    patron = (error.details or {}).get("keyPattern") or {}
    return next(iter(patron), "")


MAX_INTENTOS_TRANSACCION = 10
ESPERA_MAXIMA_REINTENTO = 0.2  # s


async def en_transaccion(db: AsyncIOMotorDatabase,
                         operacion: Callable[[AsyncIOMotorClientSession], Awaitable[T]],
                         intentos: int = MAX_INTENTOS_TRANSACCION) -> T:
    """Ejecuta `operacion(sesion)` en una transacción (RNF-FIA-03).

    Ante un error con la etiqueta TransientTransactionError (p. ej. WriteConflict entre dos transacciones que
    escriben el mismo documento) se aborta y se repite la operación completa; ante
    UnknownTransactionCommitResult se reintenta solo la confirmación.
    """
    for intento in range(1, intentos + 1):
        async with await db.client.start_session() as sesion:
            sesion.start_transaction()
            try:
                resultado = await operacion(sesion)
                await _confirmar(sesion)
                return resultado
            except PyMongoError as error:
                await _abortar(sesion)
                if error.has_error_label("TransientTransactionError") and intento < intentos:
                    log.info("Transacción transitoria fallida (%s); reintento %d", error, intento)
                    # backoff exponencial con jitter: las transacciones en conflicto no vuelven a chocar al unísono
                    await asyncio.sleep(random.uniform(0, min(ESPERA_MAXIMA_REINTENTO, 0.005 * 2 ** intento)))
                    continue
                raise
            except BaseException:
                await _abortar(sesion)
                raise
    raise RuntimeError("inalcanzable")


async def _confirmar(sesion, intentos: int = 3) -> None:
    for intento in range(1, intentos + 1):
        try:
            await sesion.commit_transaction()
            return
        except PyMongoError as error:
            if error.has_error_label("UnknownTransactionCommitResult") and intento < intentos:
                continue
            raise


async def _abortar(sesion) -> None:
    if sesion.in_transaction:
        try:
            await sesion.abort_transaction()
        except PyMongoError:
            pass


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
        await crear_indices(base_de_datos(), dominio)
        _indices_creados = True
    except (PyMongoError, RuntimeError) as error:
        log.error("No se pudieron crear los índices de MongoDB: %s", error)
