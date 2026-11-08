"""CU-10 — Responder a una publicación. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from pydantic import BaseModel, model_validator

from app.shared.domain.reglas import validar_contenido_mensaje


class MensajeEntrante(BaseModel):
    """Primer mensaje: texto (1–500) o una imagen JPG/PNG/WebP ≤ 5 MB, no ambos (RN-19, RF-CHT-01)."""

    texto: str | None = None
    imagen: bytes | None = None
    imagen_mime: str | None = None

    @model_validator(mode="after")
    def _contenido(self) -> "MensajeEntrante":
        self.texto, self.imagen_mime = validar_contenido_mensaje(self.texto, self.imagen)
        return self


class ChatCreadoResponse(BaseModel):
    chat_id: str
    nickname_autor: str
