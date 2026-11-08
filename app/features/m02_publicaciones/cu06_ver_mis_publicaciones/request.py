"""CU-06 — Ver mis publicaciones activas. DTOs Pydantic."""
from datetime import datetime

from pydantic import BaseModel

from app.shared.domain.entities import TipoPublicacion


class MiPublicacionResponse(BaseModel):
    id: str
    tipo: TipoPublicacion
    titulo: str
    fecha_creacion: datetime
    fecha_expiracion: datetime
    segundos_restantes: int


class MisPublicacionesResponse(BaseModel):
    ahora: datetime  # hora del sistema para recalcular el tiempo restante en el cliente (RF-FED-09)
    items: list[MiPublicacionResponse]
