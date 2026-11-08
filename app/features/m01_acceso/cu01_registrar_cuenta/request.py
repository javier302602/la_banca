"""CU-01 — Registrar cuenta. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from pydantic import BaseModel, Field, field_validator, model_validator

from app.shared.domain.reglas import normalizar_correo, validar_confirmacion, validar_contrasena, validar_nickname


class RegistrarCuentaRequest(BaseModel):
    """RF-AUT-01, RF-AUT-04–07, RF-AUT-14–16. El dominio se valida en el handler (depende de CFG)."""

    correo: str = Field(..., max_length=254)
    contrasena: str = Field(..., max_length=256)
    confirmacion: str = Field(..., max_length=256)
    nickname: str = Field(..., max_length=64)
    acepta_terminos: bool = False

    @field_validator("correo")
    @classmethod
    def _correo(cls, v: str) -> str:
        v = normalizar_correo(v)
        if not v:
            raise ValueError("El correo institucional es obligatorio")
        return v

    @field_validator("nickname")
    @classmethod
    def _nickname(cls, v: str) -> str:
        return validar_nickname(v)

    @field_validator("contrasena")
    @classmethod
    def _contrasena(cls, v: str) -> str:
        return validar_contrasena(v)

    @model_validator(mode="after")
    def _confirmacion_y_terminos(self) -> "RegistrarCuentaRequest":
        validar_confirmacion(self.contrasena, self.confirmacion)
        if not self.acepta_terminos:
            raise ValueError("Debes aceptar los términos de uso y la política de privacidad")  # RF-AUT-16
        return self


class MensajeResponse(BaseModel):
    mensaje: str
