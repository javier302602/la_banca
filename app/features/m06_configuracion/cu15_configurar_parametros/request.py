"""CU-15 — Configurar los parámetros del sistema. DTOs Pydantic."""
from pydantic import BaseModel, Field

from app.shared.domain.entities import ClaveParametro


class ParametroRequest(BaseModel):
    """Valor candidato para un parámetro del catálogo CFG (SRS §3.2)."""

    clave: ClaveParametro
    valor: str = Field(..., max_length=253)


class RevisionConfiguracion(BaseModel):
    """Resultado de revisar la configuración técnica: valores efectivos y valores rechazados."""

    efectivos: dict[str, str | int]
    rechazados: list[str]
