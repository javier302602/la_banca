"""CU-04 — Editar nickname. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from pydantic import BaseModel, Field

from app.shared.domain.entities import LONGITUD_NICKNAME, PATRON_NICKNAME

class EditarNicknameRequest(BaseModel):
    nickname: str = Field(..., min_length=LONGITUD_NICKNAME[0], max_length=LONGITUD_NICKNAME[1],
                          pattern=PATRON_NICKNAME)


class NicknameResponse(BaseModel):
    nickname: str
