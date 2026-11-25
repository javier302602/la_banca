"""CU-24 — Reportar videollamada. DTOs Pydantic."""
from pydantic import BaseModel, Field, field_validator

from app.shared.domain.entities import MotivoReporteVideollamada

LARGO_DETALLE = 500


class ReportarVideollamadaRequest(BaseModel):
    sala_id: str = Field(..., max_length=64)
    motivo: MotivoReporteVideollamada           # OBSCENO | INSULTOS | SPAM | OTRO
    detalle: str = ""

    @field_validator("detalle")
    @classmethod
    def _detalle(cls, valor: str) -> str:
        valor = " ".join(valor.split())
        if len(valor) > LARGO_DETALLE:
            raise ValueError(f"El detalle puede tener como máximo {LARGO_DETALLE} caracteres")
        return valor


class ReporteVideollamadaResponse(BaseModel):
    id: str
    mensaje: str
