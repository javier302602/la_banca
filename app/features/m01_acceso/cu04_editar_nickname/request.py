"""CU-04 — Editar nickname. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from pydantic import BaseModel, Field, field_validator

from app.shared.domain.reglas import validar_nickname


class EditarNicknameRequest(BaseModel):
    nickname: str = Field(..., max_length=64)

    @field_validator("nickname")
    @classmethod
    def _nickname(cls, v: str) -> str:
        return validar_nickname(v)  # RF-AUT-05


class NicknameResponse(BaseModel):
    nickname: str
