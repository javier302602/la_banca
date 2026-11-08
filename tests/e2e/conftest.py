"""Pruebas de punta a punta contra un MongoDB real (replica set). Excluidas del pytest por defecto.

Ejecutar con:  pytest -m e2e
Usa E2E_MONGO_URI (por defecto un replica set local rs0 en localhost:27017) y la base la_banca_e2e,
que se vacía al empezar.
"""
import os
from pathlib import Path

import pytest

URI_POR_DEFECTO = "mongodb://localhost:27017/?replicaSet=rs0&directConnection=true"
BASE_E2E = "la_banca_e2e"
_DIRECTORIO = Path(__file__).resolve().parent


def pytest_collection_modifyitems(config, items):
    for item in items:
        if _DIRECTORIO in Path(str(item.fspath)).resolve().parents:
            item.add_marker(pytest.mark.e2e)


@pytest.fixture(scope="session")
def entorno_e2e():
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError

    uri = os.environ.get("E2E_MONGO_URI", URI_POR_DEFECTO)
    try:
        MongoClient(uri, serverSelectionTimeoutMS=3000).admin.command("ping")
    except PyMongoError as error:
        pytest.skip(f"MongoDB de pruebas no disponible en {uri}: {error}")
    valores = {"MONGO_URI": uri, "MONGO_DB": BASE_E2E, "DOMINIO_INSTITUCIONAL": "unas.edu.pe",
               "CRON_SECRET": "s3cr3t", "APP_BASE_URL": "https://testserver",
               "IMAGE_STORAGE": "memoria", "EMAIL_SENDER": "consola", "ENTORNO": "desarrollo"}
    anteriores = {k: os.environ.get(k) for k in valores}
    os.environ.update(valores)
    MongoClient(uri).drop_database(BASE_E2E)
    yield MongoClient(uri)[BASE_E2E]
    for clave, valor in anteriores.items():
        if valor is None:
            os.environ.pop(clave, None)
        else:
            os.environ[clave] = valor
