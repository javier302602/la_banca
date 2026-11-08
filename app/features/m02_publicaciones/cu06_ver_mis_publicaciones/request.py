"""CU-06 — Ver mis publicaciones activas. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from pydantic import BaseModel

from app.shared.domain.entities import TipoPublicacion

class MiPublicacionResponse(BaseModel):
    id: str
    tipo: TipoPublicacion
    titulo: str
    segundos_restantes: int
