"""CU-15 — Configurar los parámetros del sistema. Punto de entrada técnico (sin endpoint público).

RF-CFG-08: no hay pantalla ni API de administración. El router se mantiene vacío por la forma del slice.
El responsable técnico revisa la configuración con:

    python -m app.features.m06_configuracion.cu15_configurar_parametros.endpoint [--registrar]

que muestra los valores efectivos, lista los rechazados (se conserva el último válido) y, con
--registrar, los guarda en system_parameters.
"""
import asyncio
import os
import sys

from fastapi import APIRouter

from app.shared.clock import get_clock
from app.shared.config.provider import get_config

from .handler import ConfigurarParametrosHandler

router = APIRouter(tags=["M06 Configuración"])


async def _ejecutar(registrar: bool) -> int:
    repositorio = None
    if registrar:
        from app.shared.db.mongo import get_database

        from .repository import MongoParameterRepository

        repositorio = MongoParameterRepository(get_database())
    handler = ConfigurarParametrosHandler(get_config(), repositorio, get_clock())
    revision = await handler.revisar(os.environ, registrar=registrar)
    for clave, valor in revision.efectivos.items():
        print(f"{clave} = {valor}")
    for rechazo in revision.rechazados:
        print(f"RECHAZADO: {rechazo}", file=sys.stderr)
    return 1 if revision.rechazados else 0


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_ejecutar("--registrar" in (argv if argv is not None else sys.argv[1:])))


if __name__ == "__main__":
    raise SystemExit(main())
