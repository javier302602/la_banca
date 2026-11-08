"""CU-04 — Editar nickname. Caso de uso (handler).

RF: RF-AUT-05, RF-AUT-06, RF-AUT-13, RF-AUT-26, RF-AUT-27
Valida formato (3–20, alfanumérico o guion bajo) y unicidad sin distinguir mayúsculas.

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from app.shared.domain.contracts import IAccountRepository, IClock

from .request import EditarNicknameRequest, NicknameResponse


class EditarNicknameHandler:
    def __init__(self, cuentas: IAccountRepository, clock: IClock) -> None:
        self._cuentas = cuentas
        self._clock = clock

    async def handle(self, estudiante_id: str, body: EditarNicknameRequest) -> NicknameResponse:
        """Ejecuta el caso de uso."""
        raise NotImplementedError
