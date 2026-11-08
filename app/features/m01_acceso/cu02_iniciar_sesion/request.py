"""CU-02 — Iniciar sesión. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from dataclasses import dataclass

from pydantic import BaseModel, Field, field_validator

from app.shared.domain.reglas import normalizar_correo


class IniciarSesionRequest(BaseModel):
    correo: str = Field(..., max_length=254)
    contrasena: str = Field(..., max_length=256)

    @field_validator("correo")
    @classmethod
    def _correo(cls, v: str) -> str:
        return normalizar_correo(v)


class SesionResponse(BaseModel):
    """El identificador de sesión viaja solo en la cookie HttpOnly."""

    nickname: str


@dataclass(frozen=True)
class SesionIniciada:
    token: str
    respuesta: SesionResponse
