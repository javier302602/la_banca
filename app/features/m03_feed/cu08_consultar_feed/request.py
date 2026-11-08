"""CU-08 — Consultar el feed «Ahora». DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname (RF-FED-04).
"""
from datetime import datetime

from pydantic import BaseModel, Field

from app.shared.domain.entities import TAMANO_BLOQUE_FEED, TipoPublicacion


class ConsultarFeedRequest(BaseModel):
    tipo: TipoPublicacion | None = None  # None = «Todos» (RF-FED-18)
    cursor: str | None = Field(default=None, max_length=256)


class FeedItemResponse(BaseModel):
    id: str
    tipo: TipoPublicacion
    titulo: str
    nickname_autor: str
    fecha_creacion: datetime
    fecha_expiracion: datetime
    segundos_restantes: int
    es_propia: bool  # «Tu publicación» (RF-FED-07); sin Responder ni Reportar (RF-FED-12)


class FeedResponse(BaseModel):
    ahora: datetime
    items: list[FeedItemResponse]
    siguiente_cursor: str | None = None
    tamano_bloque: int = TAMANO_BLOQUE_FEED
    mensaje_vacio: str | None = None
