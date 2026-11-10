"""CU-20 — Ver el perfil de una persona. DTOs Pydantic. Sin correo (RN-04 modificada)."""
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel

from app.shared.domain.perfiles import Apariencia


class PerfilPublicoResponse(BaseModel):
    nickname: str
    biografia: str
    fecha_ingreso: datetime
    apariencia: Apariencia
    es_propio: bool


@dataclass(frozen=True)
class FotoDescargada:
    contenido: bytes
    mime_type: str
