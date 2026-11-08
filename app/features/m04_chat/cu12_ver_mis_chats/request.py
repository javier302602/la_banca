"""CU-12 — Ver mis chats activos y abrir uno. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from datetime import datetime

from pydantic import BaseModel

class ChatResumenResponse(BaseModel):
    id: str
    titulo_publicacion: str
    nickname_contraparte: str
    segundos_restantes: int
    aviso_expiracion: bool


class MensajeResponse(BaseModel):
    id: str
    nickname_emisor: str
    texto: str | None = None
    imagen_url: str | None = None
    enviado_en: datetime


class ChatDetalleResponse(BaseModel):
    id: str
    titulo_publicacion: str
    nickname_contraparte: str
    segundos_restantes: int
    aviso_expiracion: bool
    mensajes: list[MensajeResponse]
