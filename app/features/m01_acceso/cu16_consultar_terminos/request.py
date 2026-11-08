"""CU-16 — Consultar términos de uso y política de privacidad. DTOs Pydantic."""
from pydantic import BaseModel


class TerminosResponse(BaseModel):
    version: str
    fecha: str
    texto: str
