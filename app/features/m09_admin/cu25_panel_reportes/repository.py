"""CU-25 — Panel de reportes. Implementación Mongo (la reutilizan CU-26 moderar y CU-27 historial).

Junta las dos colecciones de reportes en un solo formato (ReporteAdmin):
- reports:           publicaciones y chats (reportados por una persona o por el filtro automático).
                     Guardan una copia del contenido (texto, mensajes e imágenes retenidas).
- videocall_reports: videollamadas. No hay video guardado: solo la sala, quién reportó, a quién y por qué.
Los reportes anteriores al panel no tienen «status»: se tratan como PENDIENTE.
"""
from datetime import datetime

from pymongo import DESCENDING
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.db.mapeo import doc_a_estudiante
from app.shared.db.mongo import oid
from app.shared.domain.contracts import IAdminRepository
from app.shared.domain.entities import EstadoPublicacion, EstadoReporte, EstadoSesion, ReporteAdmin

TIPOS = {"PUBLICATION": "PUBLICACION", "CHAT": "CHAT"}
_PENDIENTE = {"$in": [None, EstadoReporte.PENDIENTE.value]}  # sin campo (anteriores al panel) o PENDIENTE


def _s(valor) -> str | None:
    return str(valor) if valor is not None else None


def _limpio(valor):
    """ObjectId y fechas a texto, para enviar la copia del contenido tal cual al navegador."""
    if isinstance(valor, dict):
        return {k: _limpio(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_limpio(v) for v in valor]
    if isinstance(valor, datetime):
        return valor.isoformat()
    if type(valor).__name__ == "ObjectId":
        return str(valor)
    return valor


def _de_contenido(d: dict) -> ReporteAdmin:
    copia = d.get("reportedContentSnapshot") or {}
    return ReporteAdmin(
        origen="contenido", id=str(d["_id"]), tipo=TIPOS.get(d["targetType"], d["targetType"]), motivo=d["reasonCode"],
        detalle=d.get("observation") or "", fecha=d["reportedAt"],
        estado=EstadoReporte(d.get("status") or EstadoReporte.PENDIENTE.value), automatico=bool(d.get("automatic")),
        reportante_id=_s(d.get("reporterId")), reportado_id=_s(copia.get("offenderUserId")), objeto_id=_s(d["targetId"]),
        contenido=_limpio({"publicacion": copia.get("publicationData"), "mensajes": copia.get("messagesSnapshot") or []}),
        imagenes=list(copia.get("retainedImageKeys") or []), acciones=_limpio(d.get("actions") or []))


def _de_videollamada(d: dict, sala: dict | None) -> ReporteAdmin:
    return ReporteAdmin(
        origen="videollamada", id=str(d["_id"]), tipo="VIDEOLLAMADA", motivo=d["reason"], detalle=d.get("detail") or "",
        fecha=d["createdAt"], estado=EstadoReporte(d.get("status") or EstadoReporte.PENDIENTE.value), automatico=False,
        reportante_id=_s(d["reporterId"]), reportado_id=_s(d["reportedId"]), objeto_id=_s(d["roomId"]),
        contenido=_limpio({"sala": {"inicio": sala.get("startedAt"), "fin": sala.get("endedAt")} if sala else None}),
        acciones=_limpio(d.get("actions") or []))


class MongoAdminRepository(IAdminRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    # --- reportes ----------------------------------------------------------------------------------------
    async def listar_reportes(self, estado, limite):
        filtro = {} if estado is None else {"status": _PENDIENTE if estado is EstadoReporte.PENDIENTE else estado.value}
        contenido = await self._db.reports.find(filtro).sort("reportedAt", DESCENDING).limit(limite).to_list(limite)
        llamadas = await self._db.videocall_reports.find(filtro).sort("createdAt", DESCENDING).limit(limite).to_list(limite)
        salas = {s["_id"]: s async for s in self._db.videocall_rooms.find({"_id": {"$in": [d["roomId"] for d in llamadas]}})}
        todos = [_de_contenido(d) for d in contenido] + [_de_videollamada(d, salas.get(d["roomId"])) for d in llamadas]
        return sorted(todos, key=lambda r: r.fecha, reverse=True)[:limite]

    async def contar_pendientes(self):
        return (await self._db.reports.count_documents({"status": _PENDIENTE})
                + await self._db.videocall_reports.count_documents({"status": _PENDIENTE}))

    async def buscar_reporte(self, origen, reporte_id):
        clave = oid(reporte_id)
        if clave is None:
            return None
        if origen == "contenido":
            d = await self._db.reports.find_one({"_id": clave})
            return _de_contenido(d) if d else None
        if origen == "videollamada":
            d = await self._db.videocall_reports.find_one({"_id": clave})
            return _de_videollamada(d, await self._db.videocall_rooms.find_one({"_id": d["roomId"]})) if d else None
        return None

    async def marcar_reporte(self, origen, reporte_id, estado, accion):
        coleccion = self._db.reports if origen == "contenido" else self._db.videocall_reports
        await coleccion.update_one({"_id": oid(reporte_id)}, {"$set": {"status": estado.value}, "$push": {"actions": accion}})

    # --- cuentas -----------------------------------------------------------------------------------------
    async def perfiles(self, ids):
        claves = [c for c in (oid(i) for i in ids if i) if c is not None]
        docs = self._db.accounts.find({"_id": {"$in": claves}}, {"nickname": 1, "fullName": 1, "career": 1})
        return {str(d["_id"]): {"nickname": d["nickname"], "nombre": d.get("fullName") or "",
                                "carrera": d.get("career") or ""} async for d in docs}

    async def buscar_cuenta(self, estudiante_id):
        clave = oid(estudiante_id)
        doc = await self._db.accounts.find_one({"_id": clave}) if clave else None
        return doc_a_estudiante(doc) if doc else None

    async def advertir(self, estudiante_id, texto):
        await self._db.accounts.update_one({"_id": oid(estudiante_id)}, {"$set": {"pendingWarning": texto}})

    async def quitar_aviso(self, estudiante_id):
        await self._db.accounts.update_one({"_id": oid(estudiante_id)}, {"$set": {"pendingWarning": None}})

    async def suspender(self, estudiante_id, hasta, ahora):
        await self._db.accounts.update_one({"_id": oid(estudiante_id)}, {"$set": {"suspendedUntil": hasta}})
        await self._cerrar_sesiones(estudiante_id, ahora)

    async def banear(self, estudiante_id, ahora):
        await self._db.accounts.update_one({"_id": oid(estudiante_id)}, {"$set": {"banned": True}})
        await self._cerrar_sesiones(estudiante_id, ahora)

    async def _cerrar_sesiones(self, estudiante_id, ahora):
        await self._db.sessions.update_many({"userId": oid(estudiante_id), "status": EstadoSesion.ACTIVE.value},
                                            {"$set": {"status": EstadoSesion.CLOSED.value, "closedAt": ahora}})

    # --- contenido ---------------------------------------------------------------------------------------
    async def eliminar_publicacion(self, publicacion_id, ahora):
        r = await self._db.publications.update_one(
            {"_id": oid(publicacion_id), "status": {"$ne": EstadoPublicacion.REMOVED.value}},
            {"$set": {"status": EstadoPublicacion.REMOVED.value, "closedAt": ahora}})
        return r.modified_count == 1

    async def eliminar_chat(self, chat_id):
        clave = oid(chat_id)
        claves = []
        async for m in self._db.messages.find({"chatId": clave}, {"imageAttachment.objectKey": 1, "documentAttachment.objectKey": 1}):
            claves += [m[c]["objectKey"] for c in ("imageAttachment", "documentAttachment") if m.get(c)]
        await self._db.messages.delete_many({"chatId": clave})
        await self._db.chats.delete_one({"_id": clave})
        await self._db.live_locations.delete_many({"chatId": clave})
        return claves

    # --- historial ---------------------------------------------------------------------------------------
    async def registrar_accion(self, accion):
        await self._db.admin_actions.insert_one(dict(accion))

    async def historial(self, limite):
        docs = await self._db.admin_actions.find().sort("at", DESCENDING).limit(limite).to_list(limite)
        return [_limpio({k: v for k, v in d.items() if k != "_id"}) for d in docs]
