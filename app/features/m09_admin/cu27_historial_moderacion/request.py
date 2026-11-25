"""CU-27 — Historial de moderación. DTOs Pydantic."""
from datetime import datetime

from pydantic import BaseModel


class AccionHistorial(BaseModel):
    fecha: datetime
    accion: str          # ELIMINAR_CONTENIDO | ADVERTIR | SUSPENDER | BANEAR | DESCARTAR
    admin: str           # nickname del administrador
    usuario: str         # nickname de la persona reportada
    tipo_reporte: str    # PUBLICACION | CHAT | VIDEOLLAMADA
    detalle: str


class HistorialResponse(BaseModel):
    acciones: list[AccionHistorial]
