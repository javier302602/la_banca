"""EA-07 — Eliminar las cuentas no activadas (y depurar sesiones vencidas). Automatismo (handler).

RF: RF-AUT-34 · Entregable 2 §7.3
Elimina las cuentas PENDIENTE_ACTIVACION con 72 h o más desde el registro, con su enlace vigente,
liberando correo y nickname. Además se aplica al consultar (CU-01, CU-02, CU-17), de modo que el
plazo se respeta con la precisión de RNF-FIA-01 aunque el cron se ejecute una vez al día.

También depura la colección sessions, que de otro modo crecería sin límite: elimina las sesiones cuyo
vencimiento tiene más de 30 días (RETENCION_SESIONES), sean activas ya vencidas, cerradas o expiradas.
Una sesión vencida ya no da acceso (EA-01); conservarla 30 días permite mostrar «Tu sesión se cerró por
inactividad» (RF-AUT-23) y diagnosticar incidencias recientes.
"""
from app.shared.domain.contracts import IAccountRepository, IClock
from app.shared.domain.entities import PLAZO_CUENTA_NO_ACTIVADA, RETENCION_SESIONES


class EliminarCuentasNoActivadasHandler:
    def __init__(self, cuentas: IAccountRepository, clock: IClock) -> None:
        self._cuentas = cuentas
        self._clock = clock

    async def handle(self) -> dict[str, int]:
        ahora = self._clock.ahora()
        eliminadas = await self._cuentas.eliminar_no_activadas(ahora - PLAZO_CUENTA_NO_ACTIVADA)
        sesiones = await self._cuentas.eliminar_sesiones_vencidas(ahora - RETENCION_SESIONES)
        return {"cuentas_eliminadas": eliminadas, "sesiones_eliminadas": sesiones}
