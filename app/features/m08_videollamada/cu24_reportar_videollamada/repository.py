"""CU-24 — Reportar videollamada. Implementación Mongo (colección videocall_reports).

Documento: {roomId, reporterId, reportedId, reason, detail, createdAt, status: "PENDIENTE"}; el panel de
administradores de la Fase 5 lo leerá y cambiará el estado. La sala se lee del repositorio de CU-23.
"""
from app.features.m08_videollamada.cu23_videollamada.repository import MongoVideollamadaRepository
from app.shared.db.mongo import oid


class MongoReportarVideollamadaRepository(MongoVideollamadaRepository):
    async def guardar_reporte(self, reporte):
        resultado = await self._db.videocall_reports.insert_one({
            "roomId": oid(reporte.sala_id), "reporterId": oid(reporte.reportante_id),
            "reportedId": oid(reporte.reportado_id), "reason": reporte.motivo.value, "detail": reporte.detalle,
            "createdAt": reporte.fecha, "status": "PENDIENTE"})
        return str(resultado.inserted_id)
