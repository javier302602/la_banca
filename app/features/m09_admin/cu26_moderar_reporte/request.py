"""CU-26 — Moderar un reporte. DTOs Pydantic."""
from pydantic import BaseModel, Field, model_validator

from app.shared.domain.entities import AccionAdmin

DIAS_MAX_SUSPENSION = 365
LARGO_MENSAJE = 500


class AccionRequest(BaseModel):
    accion: AccionAdmin                 # ELIMINAR_CONTENIDO | ADVERTIR | SUSPENDER | BANEAR | DESCARTAR
    dias: int | None = Field(default=None, ge=1, le=DIAS_MAX_SUSPENSION)  # solo para SUSPENDER
    mensaje: str = Field(default="", max_length=LARGO_MENSAJE)           # texto de la advertencia (opcional)

    @model_validator(mode="after")
    def _dias_al_suspender(self) -> "AccionRequest":
        self.mensaje = " ".join(self.mensaje.split())
        if self.accion is AccionAdmin.SUSPENDER and self.dias is None:
            raise ValueError(f"Indica cuántos días dura la suspensión (1 a {DIAS_MAX_SUSPENSION})")
        return self
