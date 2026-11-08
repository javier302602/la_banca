"""EA-07 — Eliminar las cuentas no activadas. Automatismo (handler).

RF: RF-AUT-34
Elimina cuentas PENDIENTE_ACTIVACION con más de 72 h desde el registro y sus tokens; libera correo y nickname.

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from app.shared.domain.contracts import IAccountRepository, IClock


class EliminarCuentasNoActivadasHandler:
    def __init__(self, cuentas: IAccountRepository, clock: IClock) -> None:
        self._cuentas = cuentas
        self._clock = clock

    async def handle(self) -> int:
        """Ejecuta la limpieza y devuelve la cantidad depurada."""
        raise NotImplementedError
