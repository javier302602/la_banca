"""CU-11 — Enviar mensaje en un chat. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from datetime import datetime

from pydantic import BaseModel, model_validator

from app.shared.domain.reglas import validar_contenido_mensaje


class MensajeEntrante(BaseModel):
    """Texto (1–500) o una imagen JPG/PNG/WebP ≤ 5 MB, no ambos (RN-19)."""

    texto: str | None = None
    imagen: bytes | None = None
    imagen_mime: str | None = None

    @model_validator(mode="after")
    def _contenido(self) -> "MensajeEntrante":
        self.texto, self.imagen_mime = validar_contenido_mensaje(self.texto, self.imagen)
        return self


class MensajeResponse(BaseModel):
    id: str
    es_propio: bool
    nickname_emisor: str
    texto: str | None = None
    imagen_url: str | None = None
    fecha_envio: datetime
    fecha_expiracion_chat: datetime
