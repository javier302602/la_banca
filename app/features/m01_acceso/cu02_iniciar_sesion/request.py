"""CU-02 — Iniciar sesión. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from pydantic import BaseModel, Field

from app.shared.domain.entities import LONGITUD_CONTRASENA

class IniciarSesionRequest(BaseModel):
    correo: str = Field(..., max_length=254)
    contrasena: str = Field(..., min_length=1, max_length=LONGITUD_CONTRASENA[1])


class SesionResponse(BaseModel):
    """Solo se expone el nickname; el identificador de sesión viaja en cookie HttpOnly."""

    nickname: str
