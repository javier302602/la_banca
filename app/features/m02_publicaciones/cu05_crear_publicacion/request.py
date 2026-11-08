"""CU-05 — Crear publicación. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from datetime import datetime

from pydantic import BaseModel, Field

from app.shared.domain.entities import LONGITUD_DESCRIPCION, LONGITUD_TITULO, TipoPublicacion

class CrearPublicacionRequest(BaseModel):
    tipo: TipoPublicacion
    titulo: str = Field(..., min_length=LONGITUD_TITULO[0], max_length=LONGITUD_TITULO[1])
    descripcion: str = Field(..., min_length=LONGITUD_DESCRIPCION[0], max_length=LONGITUD_DESCRIPCION[1])


class PublicacionResponse(BaseModel):
    id: str
    tipo: TipoPublicacion
    titulo: str
    descripcion: str
    nickname_autor: str
    fecha_expiracion: datetime
