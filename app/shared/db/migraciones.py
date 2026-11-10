"""Migraciones de esquema versionadas (SRS v2.0, cambio 6.2).

Cada migración es un archivo `scripts/migraciones/NNN_descripcion.py` con:

    DESCRIPCION = "texto breve"
    async def aplicar(db) -> dict:   # idempotente: aplicarla dos veces no cambia nada la segunda vez

Al arrancar la app se aplican, en orden, las que no figuran en la colección `schema_migrations`, y cada una queda
registrada (`_id` = nombre del archivo sin .py, fecha, duración, versión de la app y resumen de cambios).

Con varios procesos arrancando a la vez (workers de gunicorn, réplicas), solo uno migra: un documento de bloqueo
en `schema_migrations_lock` (con vencimiento por si un proceso muere a mitad) hace que los demás esperen y luego
encuentren todo aplicado.
"""
import asyncio
import importlib.util
import logging
import os
import re
import socket
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType

from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError

log = logging.getLogger("la_banca.migraciones")

DIRECTORIO = Path(__file__).resolve().parents[3] / "scripts" / "migraciones"
PATRON = re.compile(r"^(\d{3})_[a-z0-9_]+\.py$")
COLECCION = "schema_migrations"
BLOQUEO = "schema_migrations_lock"
VIGENCIA_BLOQUEO = timedelta(minutes=10)
ESPERA_MAXIMA_S = 120


def descubrir(directorio: Path = DIRECTORIO) -> list[tuple[str, Path]]:
    """[(nombre, ruta)] ordenadas por número. Falla si dos comparten número."""
    encontradas = sorted((p.stem, p) for p in directorio.glob("*.py") if PATRON.match(p.name))
    numeros = [n[:3] for n, _ in encontradas]
    duplicados = {n for n in numeros if numeros.count(n) > 1}
    if duplicados:
        raise RuntimeError(f"Migraciones con el mismo número: {sorted(duplicados)}")
    return encontradas


def cargar(nombre: str, ruta: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"la_banca_migracion_{nombre}", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    if not callable(getattr(modulo, "aplicar", None)):
        raise RuntimeError(f"La migración {nombre} no define aplicar(db)")
    return modulo


async def aplicadas(db: AsyncDatabase) -> set[str]:
    return {d["_id"] async for d in db[COLECCION].find({}, {"_id": 1})}


async def _tomar_bloqueo(db: AsyncDatabase, dueno: str) -> bool:
    ahora = datetime.now(timezone.utc)
    await db[BLOQUEO].delete_one({"_id": "migraciones", "venceEn": {"$lt": ahora}})  # bloqueo abandonado
    try:
        await db[BLOQUEO].insert_one({"_id": "migraciones", "dueno": dueno, "venceEn": ahora + VIGENCIA_BLOQUEO})
        return True
    except DuplicateKeyError:
        return False


async def aplicar_pendientes(db: AsyncDatabase, directorio: Path = DIRECTORIO, version_app: str = "") -> list[str]:
    """Aplica las migraciones pendientes y devuelve sus nombres (vacía si no había ninguna)."""
    disponibles = descubrir(directorio)
    if not disponibles or {n for n, _ in disponibles} <= await aplicadas(db):
        return []
    dueno = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:6]}"
    inicio_espera = time.monotonic()
    while not await _tomar_bloqueo(db, dueno):
        if time.monotonic() - inicio_espera > ESPERA_MAXIMA_S:
            raise RuntimeError("Otro proceso lleva demasiado tiempo aplicando migraciones")
        await asyncio.sleep(1)
    aplicadas_ahora: list[str] = []
    try:
        hechas = await aplicadas(db)  # otro proceso pudo terminar mientras esperábamos
        for nombre, ruta in disponibles:
            if nombre in hechas:
                continue
            modulo = cargar(nombre, ruta)
            t0 = time.monotonic()
            log.info("Aplicando migración %s: %s", nombre, getattr(modulo, "DESCRIPCION", ""))
            resumen = await modulo.aplicar(db) or {}
            await db[COLECCION].insert_one({
                "_id": nombre, "descripcion": getattr(modulo, "DESCRIPCION", ""),
                "aplicadaEn": datetime.now(timezone.utc), "duracionMs": int((time.monotonic() - t0) * 1000),
                "versionApp": version_app, "resumen": resumen})
            aplicadas_ahora.append(nombre)
            log.info("Migración %s aplicada: %s", nombre, resumen)
    finally:
        await db[BLOQUEO].delete_one({"_id": "migraciones", "dueno": dueno})
    return aplicadas_ahora


async def aplicar_al_arrancar() -> list[str]:
    """Desde el lifespan de la app. Sin MONGO_URI (pruebas unitarias) no hace nada; un fallo se registra y la app
    arranca igual: el código de v2 tolera los documentos de v1 y la migración se reintenta en el próximo arranque."""
    from app.shared.config.provider import variable
    from app.shared.db.mongo import base_de_datos
    from app.shared.version import VERSION

    if not variable("MONGO_URI"):
        return []
    try:
        return await aplicar_pendientes(base_de_datos(), version_app=VERSION)
    except Exception:
        log.exception("No se pudieron aplicar las migraciones")
        return []
