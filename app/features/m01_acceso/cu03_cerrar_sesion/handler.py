"""CU-03 — Cerrar sesión manualmente. Caso de uso (handler).

RF: RF-AUT-10, RF-AUT-20
Invalida en el servidor solo la sesión desde la que se solicita (RNF-SEG-07); las demás sesiones del
estudiante siguen abiertas (RN-38). Es idempotente: una sesión ya cerrada o expirada no produce error.
"""
from app.shared.domain.contracts import IAccountRepository, IClock, ITokenService
from app.shared.domain.entities import EstadoSesion


class CerrarSesionHandler:
    def __init__(self, cuentas: IAccountRepository, tokens: ITokenService, clock: IClock) -> None:
        self._cuentas = cuentas
        self._tokens = tokens
        self._clock = clock

    async def handle(self, token: str | None) -> None:
        if not token:
            return
        sesion = await self._cuentas.buscar_sesion_por_token(self._tokens.hash(token))
        if sesion is not None and sesion.estado is EstadoSesion.ACTIVE:
            await self._cuentas.finalizar_sesion(sesion.id, EstadoSesion.CLOSED, self._clock.ahora())
