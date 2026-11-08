"""CU-17 — Activar la cuenta. DTOs Pydantic."""
from pydantic import BaseModel, Field, field_validator

from app.shared.domain.reglas import normalizar_correo


class ActivarCuentaRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=256)


class ReenviarActivacionRequest(BaseModel):
    correo: str = Field(..., max_length=254)

    @field_validator("correo")
    @classmethod
    def _correo(cls, v: str) -> str:
        return normalizar_correo(v)


class MensajeResponse(BaseModel):
    mensaje: str
