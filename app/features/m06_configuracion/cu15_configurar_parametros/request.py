"""CU-15 — Configurar los parámetros del sistema. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from pydantic import BaseModel, Field

from app.shared.domain.entities import ClaveParametro

class ParametroRequest(BaseModel):
    """Valor candidato para un parámetro del catálogo CFG (sección 3.2)."""

    clave: ClaveParametro
    valor: str = Field(..., min_length=1, max_length=253)
