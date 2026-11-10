"""CU-09 — Ver detalle de una publicación. DTOs Pydantic."""
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel

from app.shared.domain.entities import TipoPublicacion
from app.shared.domain.perfiles import Apariencia


class DetallePublicacionResponse(BaseModel):
    ahora: datetime
    id: str
    tipo: TipoPublicacion
    titulo: str
    descripcion: str
    nickname_autor: str
    apariencia_autor: Apariencia  # SRS v2.0, cambio 2.4
    fecha_expiracion: datetime
    segundos_restantes: int
    es_propia: bool
    puede_responder: bool
    puede_reportar: bool
    chat_existente_id: str | None = None  # RF-CHT-23: ofrecer abrir el chat activo existente
    imagenes: list[str] = []  # galería: URLs de hasta 3 imágenes (SRS v2.0, cambio 3.1)


@dataclass(frozen=True)
class ImagenDescargada:
    contenido: bytes
    mime_type: str
