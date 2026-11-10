"""Conversión documento BSON ⇄ entidad, con los nombres de campo del Entregable 2 (Tablas 6.1–6.8).

Compartido por los repository.py de los slices para no duplicar el mapeo.
"""
from datetime import datetime

from bson import ObjectId

from app.shared.domain.perfiles import FotoPerfil

from app.shared.domain.entities import (
    AceptacionTerminos,
    VENTANA_ENLACES,
    Chat,
    CodigoMotivo,
    ContenidoReportado,
    EnlaceUnUso,
    EstadoChat,
    EstadoCuenta,
    EstadoPublicacion,
    EstadoSesion,
    Estudiante,
    ImagenAdjunta,
    IntentoAcceso,
    Mensaje,
    ParametroSistema,
    Publicacion,
    Reporte,
    Sesion,
    TipoObjetoReportado,
    TipoPublicacion,
)


def _s(valor) -> str:
    return str(valor) if valor is not None else ""


def _o(valor: str | None) -> ObjectId | None:
    return ObjectId(valor) if valor else None


# --- accounts -------------------------------------------------------------------
def enlace_a_doc(enlace: EnlaceUnUso, ahora: datetime | None = None) -> dict:
    envios = [t for t in enlace.envios_en if ahora is None or t > ahora - VENTANA_ENLACES]
    return {"tokenHash": enlace.token_hash, "expiresAt": enlace.expira_en,
            "sentCount": len(envios), "sentAt": envios}


def doc_a_enlace(doc: dict | None) -> EnlaceUnUso:
    doc = doc or {}
    return EnlaceUnUso(token_hash=doc.get("tokenHash"), expira_en=doc.get("expiresAt"),
                       envios_en=list(doc.get("sentAt") or []))


def estudiante_a_doc(e: Estudiante) -> dict:
    doc = {
        "email": e.correo_institucional,
        "passwordHash": e.password_hash,
        "nickname": e.nickname,
        "status": e.estado.value,
        "activation": enlace_a_doc(e.activacion),
        "passwordReset": enlace_a_doc(e.recuperacion),
        "createdAt": e.fecha_registro,
        "activatedAt": e.fecha_activacion,
        "bio": e.biografia,
        "avatar": e.avatar,
        "photo": foto_a_doc(e.foto),
    }
    if e.aceptacion:
        doc["termsAcceptance"] = {"version": e.aceptacion.version, "acceptedAt": e.aceptacion.fecha}
    if e.id:
        doc["_id"] = ObjectId(e.id)
    return doc


def doc_a_estudiante(doc: dict) -> Estudiante:
    terminos = doc.get("termsAcceptance")
    return Estudiante(
        id=_s(doc["_id"]),
        correo_institucional=doc["email"],
        password_hash=doc["passwordHash"],
        nickname=doc["nickname"],
        estado=EstadoCuenta(doc["status"]),
        fecha_registro=doc["createdAt"],
        aceptacion=AceptacionTerminos(terminos["version"], terminos["acceptedAt"]) if terminos else None,
        activacion=doc_a_enlace(doc.get("activation")),
        recuperacion=doc_a_enlace(doc.get("passwordReset")),
        fecha_activacion=doc.get("activatedAt"),
        biografia=doc.get("bio") or "",
        avatar=doc.get("avatar"),
        foto=doc_a_foto(doc.get("photo")),
    )


def foto_a_doc(foto: FotoPerfil | None) -> dict | None:
    if foto is None:
        return None
    return {"objectKey": foto.referencia, "mimeType": foto.mime_type, "updatedAt": foto.actualizada_en}


def doc_a_foto(doc: dict | None) -> FotoPerfil | None:
    if not doc or not doc.get("objectKey"):
        return None
    return FotoPerfil(doc["objectKey"], doc.get("mimeType", "image/webp"), doc["updatedAt"])


# --- login_attempts ---------------------------------------------------------------
def intento_a_doc(i: IntentoAcceso) -> dict:
    return {"email": i.correo_ingresado, "failedCount": i.conteo_fallidos, "firstFailedAt": i.primer_fallo,
            "lastFailedAt": i.ultimo_fallo, "lockedUntil": i.bloqueado_hasta, "failedAt": list(i.fallos)}


def doc_a_intento(doc: dict) -> IntentoAcceso:
    fallos = list(doc.get("failedAt") or [])
    if not fallos:  # documento anterior a la ventana móvil: se reconstruye con las marcas disponibles
        fallos = [doc["firstFailedAt"]] + [doc["lastFailedAt"]] * (doc["failedCount"] - 1)
    return IntentoAcceso(id=_s(doc.get("_id")), correo_ingresado=doc["email"], conteo_fallidos=doc["failedCount"],
                         primer_fallo=doc["firstFailedAt"], ultimo_fallo=doc["lastFailedAt"],
                         bloqueado_hasta=doc.get("lockedUntil"), fallos=fallos)


# --- sessions -----------------------------------------------------------------------
def sesion_a_doc(s: Sesion) -> dict:
    return {"userId": ObjectId(s.estudiante_id), "tokenHash": s.token_hash, "startedAt": s.fecha_inicio,
            "lastInteractionAt": s.ultima_interaccion, "expiresAt": s.fecha_expiracion,
            "closedAt": s.fecha_cierre, "status": s.estado.value}


def doc_a_sesion(doc: dict) -> Sesion:
    return Sesion(id=_s(doc["_id"]), estudiante_id=_s(doc["userId"]), token_hash=doc["tokenHash"],
                  fecha_inicio=doc["startedAt"], ultima_interaccion=doc["lastInteractionAt"],
                  fecha_expiracion=doc["expiresAt"], estado=EstadoSesion(doc["status"]),
                  fecha_cierre=doc.get("closedAt"))


# --- publications -----------------------------------------------------------------
def imagen_a_doc(i: ImagenAdjunta) -> dict:
    return {"objectKey": i.referencia, "mimeType": i.mime_type, "sizeBytes": i.tamano_bytes,
            "storageBucket": i.bucket}


def doc_a_imagen(d: dict) -> ImagenAdjunta:
    return ImagenAdjunta(d["objectKey"], d["mimeType"], d["sizeBytes"], d.get("storageBucket"))


def publicacion_a_doc(p: Publicacion) -> dict:
    return {"authorId": ObjectId(p.autor_id), "authorNickname": p.nickname_autor, "type": p.tipo.value,
            "title": p.titulo, "description": p.descripcion, "createdAt": p.fecha_creacion,
            "expiresAt": p.fecha_expiracion, "closedAt": p.fecha_cierre, "status": p.estado.value,
            "images": [imagen_a_doc(i) for i in p.imagenes]}


def doc_a_publicacion(doc: dict) -> Publicacion:
    return Publicacion(id=_s(doc["_id"]), autor_id=_s(doc["authorId"]), nickname_autor=doc["authorNickname"],
                       tipo=TipoPublicacion(doc["type"]), titulo=doc["title"], descripcion=doc["description"],
                       fecha_creacion=doc["createdAt"], fecha_expiracion=doc["expiresAt"],
                       estado=EstadoPublicacion(doc["status"]), fecha_cierre=doc.get("closedAt"),
                       imagenes=[doc_a_imagen(d) for d in doc.get("images") or []])


# --- chats / messages -----------------------------------------------------------------
def chat_a_doc(c: Chat) -> dict:
    return {
        "publicationId": ObjectId(c.publicacion_id), "authorId": ObjectId(c.autor_id),
        "responderId": ObjectId(c.respondedor_id),
        "participants": [ObjectId(c.autor_id), ObjectId(c.respondedor_id)],
        "startedAt": c.fecha_inicio, "lastActivityAt": c.ultima_actividad, "expiresAt": c.fecha_expiracion,
        "status": c.estado.value, "publicationType": c.tipo_publicacion.value,
        "publicationTitle": c.titulo_publicacion, "authorNickname": c.nickname_autor,
        "responderNickname": c.nickname_respondedor,
        "lastReadAt": dict(c.ultima_lectura),
    }


def doc_a_chat(doc: dict) -> Chat:
    return Chat(
        id=_s(doc["_id"]), publicacion_id=_s(doc["publicationId"]), autor_id=_s(doc["authorId"]),
        respondedor_id=_s(doc["responderId"]), fecha_inicio=doc["startedAt"],
        ultima_actividad=doc["lastActivityAt"], fecha_expiracion=doc["expiresAt"],
        tipo_publicacion=TipoPublicacion(doc.get("publicationType", TipoPublicacion.NECESITO.value)),
        titulo_publicacion=doc.get("publicationTitle", ""), nickname_autor=doc.get("authorNickname", ""),
        nickname_respondedor=doc.get("responderNickname", ""),
        ultima_lectura=dict(doc.get("lastReadAt") or {}), estado=EstadoChat(doc["status"]),
    )


def mensaje_a_doc(m: Mensaje) -> dict:
    doc = {"chatId": ObjectId(m.chat_id), "senderId": ObjectId(m.emisor_id), "senderNickname": m.nickname_emisor,
           "text": m.texto, "imageAttachment": None, "sentAt": m.fecha_envio}
    if m.imagen:
        doc["imageAttachment"] = imagen_a_doc(m.imagen)
    return doc


def doc_a_mensaje(doc: dict) -> Mensaje:
    adj = doc.get("imageAttachment")
    return Mensaje(id=_s(doc["_id"]), chat_id=_s(doc["chatId"]), emisor_id=_s(doc["senderId"]),
                   nickname_emisor=doc.get("senderNickname", ""), fecha_envio=doc["sentAt"], texto=doc.get("text"),
                   imagen=doc_a_imagen(adj) if adj else None)


# --- reports ---------------------------------------------------------------------------
def reporte_a_doc(r: Reporte) -> dict:
    return {
        "reporterId": ObjectId(r.reportante_id), "targetType": r.tipo_objeto.value,
        "targetId": ObjectId(r.objeto_id), "reasonCode": r.codigo_motivo.value, "observation": r.observacion,
        "reportedAt": r.fecha_reporte, "retentionEndsAt": r.fecha_retencion_fin,
        "reportedContentSnapshot": {
            "offenderUserId": ObjectId(r.contenido.usuario_reportado_id),
            "capturedAt": r.contenido.capturado_en or r.fecha_reporte,
            "publicationData": r.contenido.datos_publicacion,
            "messagesSnapshot": list(r.contenido.mensajes),
            "retainedImageKeys": list(r.contenido.snapshot_imagenes),
        },
    }


def _doc_a_contenido(snap: dict, reportado_en: datetime) -> ContenidoReportado:
    mensajes, datos = snap.get("messagesSnapshot") or [], snap.get("publicationData")
    if isinstance(mensajes, dict):  # formato anterior: un objeto con los datos y, en chats, la lista «mensajes»
        datos = datos or {k: v for k, v in mensajes.items() if k != "mensajes"} or None
        mensajes = mensajes.get("mensajes") or []
    return ContenidoReportado(_s(snap.get("offenderUserId")), list(mensajes), list(snap.get("retainedImageKeys") or []),
                              datos, snap.get("capturedAt") or reportado_en)


def doc_a_reporte(doc: dict) -> Reporte:
    snap = doc.get("reportedContentSnapshot") or {}
    return Reporte(
        id=_s(doc["_id"]), reportante_id=_s(doc["reporterId"]), tipo_objeto=TipoObjetoReportado(doc["targetType"]),
        objeto_id=_s(doc["targetId"]), codigo_motivo=CodigoMotivo(doc["reasonCode"]),
        fecha_reporte=doc["reportedAt"], fecha_retencion_fin=doc["retentionEndsAt"],
        contenido=_doc_a_contenido(snap, doc["reportedAt"]),
        observacion=doc.get("observation"),
    )


# --- system_parameters -----------------------------------------------------------------
def parametro_a_doc(p: ParametroSistema) -> dict:
    return {"_id": p.clave.value, "value": p.valor, "valueType": p.tipo_dato.value,
            "allowedRange": p.rango_permitido, "updatedAt": p.fecha_actualizacion}
