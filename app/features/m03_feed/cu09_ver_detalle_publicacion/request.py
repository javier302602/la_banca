"""CU-09 — Ver detalle de una publicación. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from pydantic import BaseModel

from app.shared.domain.entities import TipoPublicacion

class DetallePublicacionResponse(BaseModel):
    id: str
    tipo: TipoPublicacion
    titulo: str
    descripcion: str
    nickname_autor: str
    segundos_restantes: int
    es_propia: bool
    puede_responder: bool
