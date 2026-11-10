"""CU-05 — Crear publicación. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
Cualquier campo extra (p. ej. una duración) se ignora sin error (RF-PUB-16).
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.domain.entities import LONGITUD_DESCRIPCION, LONGITUD_TITULO, TipoPublicacion
from app.shared.domain.reglas import validar_longitud


class CrearPublicacionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tipo: TipoPublicacion  # obligatorio, sin valor por defecto (RF-PUB-02)
    titulo: str = Field(..., max_length=1000)
    descripcion: str = Field(..., max_length=5000)

    @field_validator("titulo")
    @classmethod
    def _titulo(cls, v: str) -> str:
        return validar_longitud(v, *LONGITUD_TITULO, "El título")  # RF-PUB-03

    @field_validator("descripcion")
    @classmethod
    def _descripcion(cls, v: str) -> str:
        return validar_longitud(v, *LONGITUD_DESCRIPCION, "La descripción")  # RF-PUB-04


class PublicacionResponse(BaseModel):
    id: str
    tipo: TipoPublicacion
    titulo: str
    descripcion: str
    nickname_autor: str
    fecha_creacion: datetime
    fecha_expiracion: datetime
    segundos_restantes: int
    imagenes: list[str] = []  # URLs de la galería (SRS v2.0, cambio 3.1)


class CupoResponse(BaseModel):
    """RF-PUB-13: «Publicaciones activas: N de M»."""

    activas: int
    maximo: int
