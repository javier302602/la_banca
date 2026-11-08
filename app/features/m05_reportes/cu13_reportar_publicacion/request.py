"""CU-13 — Reportar una publicación. DTOs Pydantic.

La respuesta no revela datos del reporte a nadie más que el reportante (RF-REP-15).
"""
from pydantic import BaseModel, Field, field_validator

from app.shared.domain.entities import LONGITUD_OBSERVACION, CodigoMotivo
from app.shared.domain.reglas import normalizar_texto


class ReporteRequest(BaseModel):
    codigo_motivo: CodigoMotivo | None = Field(default=None, validate_default=True)
    observacion: str | None = Field(default=None, max_length=3000)

    @field_validator("codigo_motivo")
    @classmethod
    def _motivo(cls, v: CodigoMotivo | None) -> CodigoMotivo:
        if v is None:
            raise ValueError("Selecciona un motivo")  # RF-REP-03
        return v

    @field_validator("observacion")
    @classmethod
    def _observacion(cls, v: str | None) -> str | None:
        texto = normalizar_texto(v)
        if len(texto) > LONGITUD_OBSERVACION:
            raise ValueError(f"La observación admite hasta {LONGITUD_OBSERVACION} caracteres")  # RF-REP-04
        return texto or None


class ReporteResponse(BaseModel):
    mensaje: str
