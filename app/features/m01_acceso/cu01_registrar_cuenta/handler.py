"""CU-01 — Registrar cuenta. Caso de uso (handler).

RF: RF-AUT-01–07, RF-AUT-14–17, RF-AUT-28, RF-AUT-41–43
Crea la cuenta en estado PENDIENTE_ACTIVACION (sin sesión) y envía el enlace de activación con token de un solo uso (vigencia 24 h; máx. 5 envíos por correo en 24 h).

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from app.shared.domain.contracts import IAccountRepository, IClock, IConfigurationProvider, IEmailSender, IPasswordHasher, ITokenService

from .request import MensajeResponse, RegistrarCuentaRequest


class RegistrarCuentaHandler:
    def __init__(self, cuentas: IAccountRepository, hasher: IPasswordHasher, tokens: ITokenService, correo: IEmailSender, config: IConfigurationProvider, clock: IClock) -> None:
        self._cuentas = cuentas
        self._hasher = hasher
        self._tokens = tokens
        self._correo = correo
        self._config = config
        self._clock = clock

    async def handle(self, body: RegistrarCuentaRequest) -> MensajeResponse:
        """Ejecuta el caso de uso."""
        raise NotImplementedError
