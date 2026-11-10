"""CU-11 — Enviar mensaje en un chat. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from datetime import datetime

from pydantic import BaseModel, model_validator

from app.shared.domain.reglas import validar_contenido_chat


class MensajeEntrante(BaseModel):
    """Texto (1–500), una imagen JPG/PNG/WebP ≤ 5 MB, un sticker del paquete o un documento ≤ 10 MB: solo uno
    (RN-19 modificada por el SRS v2.0)."""

    texto: str | None = None
    imagen: bytes | None = None
    imagen_mime: str | None = None
    sticker: str | None = None
    documento: bytes | None = None
    documento_nombre: str | None = None

    @model_validator(mode="after")
    def _contenido(self) -> "MensajeEntrante":
        self.sticker = (self.sticker or "").strip() or None
        self.texto, self.imagen_mime = validar_contenido_chat(self.texto, self.imagen, self.sticker, self.documento)
        return self


class DocumentoResponse(BaseModel):
    nombre: str
    tipo: str          # pdf | docx | xlsx | pptx | txt (para el icono)
    tamano_bytes: int
    url: str


class MensajeResponse(BaseModel):
    id: str
    es_propio: bool
    nickname_emisor: str
    texto: str | None = None
    imagen_url: str | None = None
    sticker: str | None = None
    sticker_url: str | None = None
    documento: DocumentoResponse | None = None
    fecha_envio: datetime
    hora: str  # HH:MM en America/Lima (RF-CHT-11, RN-34)
    fecha_expiracion_chat: datetime
