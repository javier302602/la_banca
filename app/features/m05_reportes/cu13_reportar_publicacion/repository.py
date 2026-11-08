"""CU-13 — Reportar una publicación. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.db.mapeo import doc_a_publicacion, reporte_a_doc
from app.shared.db.mongo import oid
from app.shared.domain.contracts import IPublicationRepository, IReportRepository


class MongoPublicacionLecturaRepository(IPublicationRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def buscar_por_id(self, publicacion_id):
        clave = oid(publicacion_id)
        doc = await self._db.publications.find_one({"_id": clave}) if clave else None
        return doc_a_publicacion(doc) if doc else None


class MongoReportarPublicacionRepository(IReportRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def existe_reporte(self, reportante_id, tipo, objeto_id):
        return await self._db.reports.count_documents(
            {"targetType": tipo.value, "targetId": oid(objeto_id), "reporterId": oid(reportante_id)}, limit=1) > 0

    async def crear(self, reporte):
        # Un solo documento con el subdocumento reportedContentSnapshot: atómico (RNF-FIA-03)
        resultado = await self._db.reports.insert_one(reporte_a_doc(reporte))
        return str(resultado.inserted_id)
