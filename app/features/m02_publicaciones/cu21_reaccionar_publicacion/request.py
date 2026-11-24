"""CU-21 — Reaccionar a una publicación. DTOs Pydantic."""
from pydantic import BaseModel

from app.shared.domain.entities import ResumenReacciones, TipoReaccion


class ReaccionarRequest(BaseModel):
    tipo: TipoReaccion | None = None  # None = quitar mi reacción


class ReaccionesResponse(BaseModel):
    """Conteo por tipo y la reacción del estudiante que consulta (la usan también el feed y el detalle)."""

    conteos: dict[TipoReaccion, int] = {}
    total: int = 0
    mia: TipoReaccion | None = None

    @classmethod
    def desde(cls, resumen: ResumenReacciones | None) -> "ReaccionesResponse":
        if resumen is None:
            return cls()
        return cls(conteos=resumen.conteos, total=sum(resumen.conteos.values()), mia=resumen.mia)
