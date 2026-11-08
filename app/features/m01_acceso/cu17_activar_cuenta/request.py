"""CU-17 — Activar la cuenta. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from pydantic import BaseModel, Field

class ActivarCuentaRequest(BaseModel):
    token: str = Field(..., min_length=16, max_length=256)


class ReenviarActivacionRequest(BaseModel):
    correo: str = Field(..., max_length=254)


class MensajeResponse(BaseModel):
    """Respuesta uniforme: no revela si el correo existe."""

    mensaje: str
