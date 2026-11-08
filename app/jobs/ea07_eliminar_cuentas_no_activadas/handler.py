"""EA-07 — Eliminar las cuentas no activadas. Automatismo (handler).

RF: RF-AUT-34
Elimina las cuentas PENDIENTE_ACTIVACION con 72 h o más desde el registro, con su enlace vigente,
liberando correo y nickname. Además se aplica al consultar (CU-01, CU-02, CU-17), de modo que el
plazo se respeta con la precisión de RNF-FIA-01 aunque el cron se ejecute una vez al día.
"""
from app.shared.domain.contracts import IAccountRepository, IClock
from app.shared.domain.entities import PLAZO_CUENTA_NO_ACTIVADA


class EliminarCuentasNoActivadasHandler:
    def __init__(self, cuentas: IAccountRepository, clock: IClock) -> None:
        self._cuentas = cuentas
        self._clock = clock

    async def handle(self) -> dict[str, int]:
        eliminadas = await self._cuentas.eliminar_no_activadas(self._clock.ahora() - PLAZO_CUENTA_NO_ACTIVADA)
        return {"cuentas_eliminadas": eliminadas}
