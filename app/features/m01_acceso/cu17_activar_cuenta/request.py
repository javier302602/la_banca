"""CU-17 — Activar la cuenta. DTOs Pydantic."""
from pydantic import BaseModel, Field, field_validator

from app.shared.domain.reglas import normalizar_correo


class ActivarCuentaRequest(BaseModel):
    correo: str = Field(..., max_length=254)
    codigo: str = Field(..., max_length=16)

    @field_validator("correo")
    @classmethod
    def _correo(cls, v: str) -> str:
        return normalizar_correo(v)

    @field_validator("codigo")
    @classmethod
    def _codigo(cls, v: str) -> str:
        v = v.replace(" ", "")
        if len(v) != 6 or not (v.isascii() and v.isdigit()):
            raise ValueError("El código tiene 6 dígitos")
        return v


class ReenviarActivacionRequest(BaseModel):
    correo: str = Field(..., max_length=254)

    @field_validator("correo")
    @classmethod
    def _correo(cls, v: str) -> str:
        return normalizar_correo(v)


class MensajeResponse(BaseModel):
    mensaje: str
