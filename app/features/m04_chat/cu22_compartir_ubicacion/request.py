"""CU-22 — Compartir ubicación. Mensajes JSON que viajan por el WebSocket.

Navegador → servidor:  {"tipo": "posicion", "lat": -9.29, "lng": -76.0, "precision": 12}
                       {"tipo": "detener"}
Servidor → navegador:  {"tipo": "posicion", "nickname": "ana_07", "lat": …, "lng": …, "precision": …, "actualizado": "…"}
                       {"tipo": "detenido"}                            la otra persona dejó de compartir
                       {"tipo": "error", "mensaje": "…"}
"""
from typing import Literal

from pydantic import BaseModel, Field


class PosicionEntrante(BaseModel):
    tipo: Literal["posicion"]
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    precision: float = Field(..., ge=0, le=100_000)  # metros, según el navegador


class DetenerEntrante(BaseModel):
    tipo: Literal["detener"]
