"""CU-03 — Cerrar sesión manualmente. Caso de uso (handler).

RF: RF-AUT-10, RF-AUT-20
Cierra solo la sesión actual; las demás sesiones del estudiante no se afectan.

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from app.shared.domain.contracts import IAccountRepository, IClock


class CerrarSesionHandler:
    def __init__(self, cuentas: IAccountRepository, clock: IClock) -> None:
        self._cuentas = cuentas
        self._clock = clock

    async def handle(self, estudiante_id: str) -> None:
        """Ejecuta el caso de uso."""
        raise NotImplementedError
