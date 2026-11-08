"""CU-11 — Enviar mensaje en un chat. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.shared.domain.entities import LONGITUD_MENSAJE

class MensajeEntrante(BaseModel):
    """Texto opcional (≤ 500) + imagen opcional; al menos uno de los dos (RF-CHT-08, RF-CHT-09)."""

    texto: str | None = Field(default=None, max_length=LONGITUD_MENSAJE)
    imagen_bytes: bytes | None = None
    imagen_mime: str | None = None

    @model_validator(mode="after")
    def _contenido(self) -> "MensajeEntrante":
        """Exige texto o imagen; imagen en FORMATOS_IMAGEN y ≤ TAMANO_MAX_IMAGEN."""
        raise NotImplementedError


class MensajeResponse(BaseModel):
    id: str
    nickname_emisor: str
    texto: str | None = None
    imagen_url: str | None = None
    enviado_en: datetime
