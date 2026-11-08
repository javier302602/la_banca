"""CU-18 — Recuperar la contraseña. DTOs Pydantic."""
from pydantic import BaseModel, Field, ValidationInfo, field_validator

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

    @field_validator("confirmacion")
    @classmethod
    def _confirmacion(cls, v: str, info: ValidationInfo) -> str:
        if "contrasena" in info.data:
            validar_confirmacion(info.data["contrasena"], v)  # RF-AUT-15
        return v


class MensajeResponse(BaseModel):
    mensaje: str
