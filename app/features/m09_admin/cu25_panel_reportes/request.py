"""CU-25 — Panel de reportes. DTOs Pydantic (solo para administradores)."""
from datetime import datetime

from pydantic import BaseModel


class PerfilBreve(BaseModel):
    id: str
    nickname: str
    nombre: str = ""
    carrera: str = ""


class ReporteAdminResponse(BaseModel):
    origen: str                       # contenido | videollamada (forma parte de la URL de las acciones)
    id: str
    tipo: str                         # PUBLICACION | CHAT | VIDEOLLAMADA
    motivo: str
    detalle: str
    fecha: datetime
    estado: str                       # PENDIENTE | RESUELTO | DESCARTADO
    automatico: bool
    reportante: PerfilBreve | None    # None: lo marcó el filtro automático
    reportado: PerfilBreve | None
    objeto_id: str | None
    contenido: dict                   # publicación, mensajes del chat o datos de la sala (sin video)
    imagenes: list[str]               # URLs de las imágenes y archivos retenidos al reportar
    archivos: dict[str, str]          # clave retenida → URL (los mensajes del chat la citan como imageKey/document.key)
    acciones: list[dict]


class PanelResponse(BaseModel):
    pendientes: int
    reportes: list[ReporteAdminResponse]


class PendientesResponse(BaseModel):
    pendientes: int
