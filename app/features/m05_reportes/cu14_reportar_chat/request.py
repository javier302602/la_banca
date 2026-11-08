"""CU-14 — Reportar un chat. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from pydantic import BaseModel, Field

from app.shared.domain.entities import CodigoMotivo, LONGITUD_OBSERVACION

class ReporteRequest(BaseModel):
    codigo_motivo: CodigoMotivo
    observacion: str | None = Field(default=None, max_length=LONGITUD_OBSERVACION)


class ReporteResponse(BaseModel):
    reporte_id: str
    mensaje: str
