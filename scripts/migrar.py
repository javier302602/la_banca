"""Aplica las migraciones pendientes o muestra su estado (la app ya las aplica sola al arrancar).

    docker compose exec app python -m scripts.migrar            # aplica las pendientes
    docker compose exec app python -m scripts.migrar --estado   # lista aplicadas y pendientes
"""
import argparse
import asyncio
import sys


async def principal(estado: bool) -> int:
    from app.shared.db import migraciones
    from app.shared.db.mongo import base_de_datos
    from app.shared.version import VERSION

    db = base_de_datos()
    if estado:
        hechas = await migraciones.aplicadas(db)
        for nombre, _ in migraciones.descubrir():
            print(f"{'aplicada ' if nombre in hechas else 'PENDIENTE'}  {nombre}")
        return 0
    aplicadas = await migraciones.aplicar_pendientes(db, version_app=VERSION)
    print("Aplicadas: " + ", ".join(aplicadas) if aplicadas else "No había migraciones pendientes")
    return 0


if __name__ == "__main__":
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--estado", action="store_true")
    sys.exit(asyncio.run(principal(analizador.parse_args().estado)))
