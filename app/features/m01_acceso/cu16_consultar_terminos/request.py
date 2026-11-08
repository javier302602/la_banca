"""CU-16 — Consultar términos de uso y política de privacidad. DTOs Pydantic.

Los DTOs de respuesta nunca exponen el correo institucional, solo el nickname.
"""
from pydantic import BaseModel

class TerminosResponse(BaseModel):
    version: str
    terminos_html: str
    politica_privacidad_html: str
