"""CU-01 — Registrar cuenta. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from pydantic import BaseModel, Field, field_validator, model_validator

from app.shared.domain.entities import LONGITUD_CONTRASENA, LONGITUD_NICKNAME, PATRON_NICKNAME

class RegistrarCuentaRequest(BaseModel):
    """Datos de registro (RF-AUT-01–07, RF-AUT-14–17). El dominio se valida en el handler (CFG)."""

    correo: str = Field(..., max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    contrasena: str = Field(..., min_length=LONGITUD_CONTRASENA[0], max_length=LONGITUD_CONTRASENA[1])
    confirmacion: str
    nickname: str = Field(..., min_length=LONGITUD_NICKNAME[0], max_length=LONGITUD_NICKNAME[1],
                          pattern=PATRON_NICKNAME)
    acepta_terminos: bool

    @field_validator("contrasena")
    @classmethod
    def _politica_contrasena(cls, v: str) -> str:
        """RN-30: al menos una letra y un dígito."""
        raise NotImplementedError

    @model_validator(mode="after")
    def _confirmacion_y_terminos(self) -> "RegistrarCuentaRequest":
        """La confirmación coincide y se aceptan términos y política (RF-AUT-16, RF-AUT-17)."""
        raise NotImplementedError


class MensajeResponse(BaseModel):
    mensaje: str
