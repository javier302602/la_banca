"""EA-07 — Eliminar las cuentas no activadas. Implementación Mongo de lo que necesita el job.

La consulta recorre el índice ix_accounts_activation_exp {activation.expiresAt: 1} (Entregable 2, §5.4):
- toda cuenta pendiente tiene un enlace vigente o vencido con `activation.expiresAt` (al activarse pasa a null,
  así que las cuentas activas quedan fuera del rango del índice);
- un enlace solo se emite mientras la cuenta existe, es decir, antes de cumplir 72 h, y vence 24 h después;
  por tanto, una cuenta registrada antes de `registradas_antes_de` tiene
  `activation.expiresAt ≤ registradas_antes_de + 72 h + 24 h`.
Ese límite acota el recorrido del índice; la condición exacta (RN-43) sigue siendo `createdAt ≤ registradas_antes_de`.
"""
import logging
from datetime import datetime

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import OperationFailure

from app.shared.domain.contracts import IAccountRepository
from app.shared.domain.entities import PLAZO_CUENTA_NO_ACTIVADA, VIGENCIA_ENLACE_ACTIVACION, EstadoCuenta

INDICE = "ix_accounts_activation_exp"
log = logging.getLogger("la_banca.ea07")


async def _borrar_con_indice(coleccion: AsyncCollection, filtro: dict, indice: str) -> int:
    """delete_many con hint; si el índice no existe (base recién creada o índices sin crear), repite sin hint:
    el resultado es el mismo y solo cambia el rendimiento, así que la purga nunca queda bloqueada."""
    try:
        return (await coleccion.delete_many(filtro, hint=indice)).deleted_count
    except OperationFailure as error:
        if "hint" not in str(error).lower():
            raise
        log.warning("Falta el índice %s en %s; se elimina sin hint", indice, coleccion.name)
        return (await coleccion.delete_many(filtro)).deleted_count


def filtro_no_activadas(registradas_antes_de: datetime) -> dict:
    limite_enlace = registradas_antes_de + PLAZO_CUENTA_NO_ACTIVADA + VIGENCIA_ENLACE_ACTIVACION
    return {"activation.expiresAt": {"$lte": limite_enlace},
            "status": EstadoCuenta.PENDIENTE_ACTIVACION.value,
            "createdAt": {"$lte": registradas_antes_de}}


class MongoEliminarCuentasRepository(IAccountRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def eliminar_no_activadas(self, registradas_antes_de):
        # El enlace va embebido en la cuenta y se elimina con ella
        return await _borrar_con_indice(self._db.accounts, filtro_no_activadas(registradas_antes_de), INDICE)

    async def eliminar_sesiones_vencidas(self, vencidas_antes_de):
        # ix_sessions_exp {expiresAt}. Una sesión cerrada manualmente vence como mucho 72 h (máximo de
        # CFG_HORAS_INACTIVIDAD_SESION) después de su última interacción, así que también entra.
        return await _borrar_con_indice(self._db.sessions, {"expiresAt": {"$lte": vencidas_antes_de}},
                                        "ix_sessions_exp")
