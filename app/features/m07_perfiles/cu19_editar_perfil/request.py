"""CU-19 — Editar mi perfil. DTOs Pydantic.

Ninguna respuesta incluye el correo institucional (RN-04 modificada).
"""
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.shared.config.carreras import carreras
from app.shared.domain.perfiles import AVATARES, BIOGRAFIA_MAX, Apariencia

LARGO_IDENTIDAD = 80


class EditarPerfilRequest(BaseModel):
    biografia: str = ""
    avatar: str | None = None  # avatar-NN del catálogo, o None para usar las iniciales

    @field_validator("biografia")
    @classmethod
    def _biografia(cls, valor: str) -> str:
        valor = " ".join(valor.split())  # sin saltos de línea ni espacios repetidos
        if len(valor) > BIOGRAFIA_MAX:
            raise ValueError(f"La biografía puede tener como máximo {BIOGRAFIA_MAX} caracteres")
        return valor

    @field_validator("avatar")
    @classmethod
    def _avatar(cls, valor: str | None) -> str | None:
        if valor in (None, ""):
            return None
        if valor not in AVATARES:
            raise ValueError("Elige uno de los avatares disponibles")
        return valor


class EditarIdentidadRequest(BaseModel):
    """Fase 4: nombre (2–80 caracteres) y carrera, que debe ser una de config/carreras.json."""

    nombre: str
    carrera: str

    @field_validator("nombre", "carrera")
    @classmethod
    def _texto(cls, valor: str, info) -> str:
        valor = " ".join(valor.split())
        campo = "El nombre" if info.field_name == "nombre" else "La carrera"
        if not 2 <= len(valor) <= LARGO_IDENTIDAD:
            raise ValueError(f"{campo} debe tener entre 2 y {LARGO_IDENTIDAD} caracteres")
        if info.field_name == "carrera" and valor not in carreras():
            raise ValueError("Elige una carrera de la lista")
        return valor


class MiPerfilResponse(BaseModel):
    nickname: str
    biografia: str
    avatar: str | None
    tiene_foto: bool
    apariencia: Apariencia
    fecha_ingreso: datetime
    nombre: str = ""   # solo para ti y, en la videollamada, para la otra persona
    carrera: str = ""
