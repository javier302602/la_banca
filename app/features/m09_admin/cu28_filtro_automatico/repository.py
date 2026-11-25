"""CU-28 — Filtro automático. Implementación Mongo: guarda el reporte automático en la colección reports.

Mismo formato que los reportes de las personas (CU-13 / CU-14), con reporterId nulo y automatic=True, para que
el panel (CU-25) los muestre juntos.
"""
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.db.mongo import oid
from app.shared.domain.entities import CodigoMotivo, EstadoReporte


class MongoFiltroRepository:
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def crear_reporte_automatico(self, tipo: str, objeto_id: str, ofensor_id: str, palabras: list[str],
                                       publicacion: dict | None, mensajes: list[dict], ahora, retencion_fin) -> str:
        resultado = await self._db.reports.insert_one({
            "reporterId": None, "automatic": True, "status": EstadoReporte.PENDIENTE.value,
            "targetType": tipo, "targetId": oid(objeto_id), "reasonCode": CodigoMotivo.INAPPROPRIATE.value,
            "observation": "Filtro automático: " + ", ".join(palabras),
            "reportedAt": ahora, "retentionEndsAt": retencion_fin,
            "reportedContentSnapshot": {"offenderUserId": oid(ofensor_id), "capturedAt": ahora,
                                        "publicationData": publicacion, "messagesSnapshot": mensajes,
                                        "retainedImageKeys": []}})
        return str(resultado.inserted_id)
