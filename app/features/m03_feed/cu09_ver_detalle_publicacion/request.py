"""CU-09 — Ver detalle de una publicación. DTOs Pydantic."""
from datetime import datetime

from pydantic import BaseModel

from app.shared.domain.entities import TipoPublicacion


class DetallePublicacionResponse(BaseModel):
    ahora: datetime
    id: str
    tipo: TipoPublicacion
    titulo: str
    descripcion: str
    nickname_autor: str
    fecha_expiracion: datetime
    segundos_restantes: int
    es_propia: bool
    puede_responder: bool
    puede_reportar: bool
    chat_existente_id: str | None = None  # RF-CHT-23: ofrecer abrir el chat activo existente
