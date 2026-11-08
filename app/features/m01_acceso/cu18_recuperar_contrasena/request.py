"""CU-18 — Recuperar la contraseña. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from pydantic import BaseModel, Field, model_validator

from app.shared.domain.entities import LONGITUD_CONTRASENA

class SolicitarRecuperacionRequest(BaseModel):
    correo: str = Field(..., max_length=254)


class RestablecerContrasenaRequest(BaseModel):
    token: str = Field(..., min_length=16, max_length=256)
    contrasena: str = Field(..., min_length=LONGITUD_CONTRASENA[0], max_length=LONGITUD_CONTRASENA[1])
    confirmacion: str

    @model_validator(mode="after")
    def _politica_y_confirmacion(self) -> "RestablecerContrasenaRequest":
        """RN-30 y coincidencia con la confirmación."""
        raise NotImplementedError


class MensajeResponse(BaseModel):
    mensaje: str
