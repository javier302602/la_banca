"""CU-18 — Recuperar la contraseña. Caso de uso (handler).

RF: RF-AUT-35–39, RF-AUT-48–50
Solicitud con respuesta uniforme; enlace con token de un solo uso (vigencia 30 min). Al restablecer se invalida el token y se cierran las sesiones abiertas.

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from app.shared.domain.contracts import IAccountRepository, IClock, IEmailSender, IPasswordHasher, ITokenService

from .request import MensajeResponse, RestablecerContrasenaRequest, SolicitarRecuperacionRequest


class RecuperarContrasenaHandler:
    def __init__(self, cuentas: IAccountRepository, tokens: ITokenService, hasher: IPasswordHasher, correo: IEmailSender, clock: IClock) -> None:
        self._cuentas = cuentas
        self._tokens = tokens
        self._hasher = hasher
        self._correo = correo
        self._clock = clock

    async def handle(self, body: SolicitarRecuperacionRequest) -> MensajeResponse:
        """Ejecuta el caso de uso."""
        raise NotImplementedError

    async def restablecer(self, body: RestablecerContrasenaRequest) -> MensajeResponse:
        """Ejecuta el caso de uso."""
        raise NotImplementedError
