"""RNF-MAN-02 — Control del reloj en un entorno de pruebas desplegado.

Solo responde con ENTORNO=pruebas (en cualquier otro entorno, 404, como una ruta inexistente) y exige
`Authorization: Bearer <CRON_SECRET>`. Permite comprobar los plazos de 24 h y 72 h sin esperarlos:

    curl -X POST -H "Authorization: Bearer $CRON_SECRET" -H "Content-Type: application/json" \
         -d '{"horas": 24}' https://<entorno-de-pruebas>/pruebas/reloj/avanzar
"""
import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.shared.clock import en_entorno_de_pruebas, reloj_de_pruebas

router = APIRouter(tags=["Pruebas"], include_in_schema=False)


def solo_en_pruebas(authorization: str | None = Header(default=None)) -> None:
    if not en_entorno_de_pruebas():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    secreto = os.environ.get("CRON_SECRET", "")
    if not secreto or authorization is None or not hmac.compare_digest(authorization, f"Bearer {secreto}"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autorizado")


class Avance(BaseModel):
    dias: int = Field(default=0, ge=0, le=365)
    horas: int = Field(default=0, ge=0, le=24 * 365)
    minutos: int = Field(default=0, ge=0, le=60 * 24 * 365)


def _estado() -> dict:
    reloj = reloj_de_pruebas()
    return {"ahora": reloj.ahora().isoformat(), "desfase_segundos": int(reloj.desfase.total_seconds())}


@router.get("/pruebas/reloj", dependencies=[Depends(solo_en_pruebas)])
async def consultar_reloj() -> dict:
    return _estado()


@router.post("/pruebas/reloj/avanzar", dependencies=[Depends(solo_en_pruebas)])
async def avanzar_reloj(avance: Avance) -> dict:
    from datetime import timedelta

    reloj_de_pruebas().avanzar(timedelta(days=avance.dias, hours=avance.horas, minutes=avance.minutos))
    return _estado()


@router.post("/pruebas/reloj/reiniciar", dependencies=[Depends(solo_en_pruebas)])
async def reiniciar_reloj() -> dict:
    reloj_de_pruebas().reiniciar()
    return _estado()
