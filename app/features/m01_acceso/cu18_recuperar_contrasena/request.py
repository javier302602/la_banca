"""CU-18 — Recuperar la contraseña. DTOs Pydantic."""
from pydantic import BaseModel, Field, field_validator, model_validator

from app.shared.domain.reglas import normalizar_correo, validar_confirmacion, validar_contrasena


class SolicitarRecuperacionRequest(BaseModel):
    correo: str = Field(..., max_length=254)

    @field_validator("correo")
    @classmethod
    def _correo(cls, v: str) -> str:
        return normalizar_correo(v)


class RestablecerContrasenaRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=256)
    contrasena: str = Field(..., max_length=256)
    confirmacion: str = Field(..., max_length=256)

    @field_validator("contrasena")
    @classmethod
    def _contrasena(cls, v: str) -> str:
        return validar_contrasena(v)  # RF-AUT-37 → RF-AUT-14

    @model_validator(mode="after")
    def _confirmacion(self) -> "RestablecerContrasenaRequest":
        validar_confirmacion(self.contrasena, self.confirmacion)  # RF-AUT-15
        return self


class MensajeResponse(BaseModel):
    mensaje: str
