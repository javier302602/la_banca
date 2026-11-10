"""CU-12 — Ver mis chats activos y abrir uno. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel

from app.shared.domain.entities import TipoPublicacion
from app.shared.domain.perfiles import Apariencia


class AbrirChatRequest(BaseModel):
    despues_de: datetime | None = None  # sondeo incremental: solo mensajes posteriores


class AvisoExpiracion(BaseModel):
    """EA-04 / RF-CHT-14."""

    activo: bool
    minutos: int
    mensaje: str | None = None


class ChatResumenResponse(BaseModel):
    id: str
    tipo_publicacion: TipoPublicacion
    titulo_publicacion: str
    nickname_contraparte: str
    apariencia_contraparte: Apariencia  # SRS v2.0, cambio 2.4
    ultimo_mensaje_en: datetime
    hora_ultimo_mensaje: str  # HH:MM en America/Lima (RF-CHT-18, RN-34)
    fecha_expiracion: datetime
    no_leidos: bool  # RF-CHT-21


class MisChatsResponse(BaseModel):
    ahora: datetime
    items: list[ChatResumenResponse]


class MensajeResponse(BaseModel):
    id: str
    es_propio: bool
    nickname_emisor: str
    texto: str | None = None
    imagen_url: str | None = None
    fecha_envio: datetime
    hora: str  # HH:MM en America/Lima (RF-CHT-11, RN-34)


class ChatDetalleResponse(BaseModel):
    ahora: datetime
    id: str
    tipo_publicacion: TipoPublicacion
    titulo_publicacion: str
    nickname_contraparte: str
    apariencia_contraparte: Apariencia  # SRS v2.0, cambio 2.4
    fecha_expiracion: datetime
    segundos_restantes: int
    aviso: AvisoExpiracion
    mensajes: list[MensajeResponse]


@dataclass(frozen=True)
class ImagenDescargada:
    contenido: bytes
    mime_type: str
