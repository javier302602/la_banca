"""CU-05 contra MongoDB real: creaciones simultáneas del mismo autor no superan el máximo (RF-PUB-06)."""
import asyncio
from datetime import datetime, timezone

from bson import ObjectId

from app.features.m02_publicaciones.cu05_crear_publicacion.handler import CrearPublicacionHandler
from app.features.m02_publicaciones.cu05_crear_publicacion.repository import MongoCrearPublicacionRepository
from app.features.m02_publicaciones.cu05_crear_publicacion.request import CrearPublicacionRequest
from app.shared.clock import SystemClock
from app.shared.domain.errors import Conflicto
from tests.fakes import FakeConfig


def test_creaciones_simultaneas_respetan_el_maximo(entorno_e2e):
    db_sync = entorno_e2e
    autor = ObjectId()
    db_sync.accounts.insert_one({"_id": autor, "email": "concurrente@unas.edu.pe", "passwordHash": "x" * 60,
                                 "nickname": "concurrente", "status": "ACTIVA",
                                 "createdAt": datetime.now(timezone.utc)})

    async def escenario():
        from app.shared.db.mongo import base_de_datos, crear_indices

        db = base_de_datos()
        await crear_indices(db, "unas.edu.pe")
        handler = CrearPublicacionHandler(MongoCrearPublicacionRepository(db), FakeConfig(), SystemClock())
        solicitud = CrearPublicacionRequest(tipo="NECESITO", titulo="simultánea", descripcion="d")
        return await asyncio.gather(*(handler.handle(str(autor), "concurrente", solicitud) for _ in range(12)),
                                    return_exceptions=True)

    resultados = asyncio.run(escenario())
    creadas = [r for r in resultados if not isinstance(r, Exception)]
    rechazadas = [r for r in resultados if isinstance(r, Conflicto)]
    assert len(creadas) == 3 and len(rechazadas) == 9, resultados
    assert db_sync.publications.count_documents({"authorId": autor}) == 3
    assert db_sync.accounts.find_one({"_id": autor})["publicationsVersion"] == 12
