"""CU-08 — Consultar el feed «Ahora». DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from pydantic import BaseModel, Field

from app.shared.domain.entities import TAMANO_BLOQUE_FEED, TipoPublicacion

class ConsultarFeedRequest(BaseModel):
    tipo: TipoPublicacion | None = None
    cursor: str | None = Field(default=None, max_length=128)


class FeedItemResponse(BaseModel):
    id: str
    tipo: TipoPublicacion
    titulo: str
    nickname_autor: str
    segundos_restantes: int
    es_propia: bool


class FeedResponse(BaseModel):
    items: list[FeedItemResponse]
    siguiente_cursor: str | None = None
    tamano_bloque: int = TAMANO_BLOQUE_FEED
