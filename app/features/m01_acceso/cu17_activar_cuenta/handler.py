"""CU-17 — Activar la cuenta. Caso de uso (handler).

RF: RF-AUT-29, RF-AUT-31–33, RF-AUT-44–47
El enlace lleva un token de un solo uso (vigencia 24 h). Al activar se invalida el token. A1: reenvío de enlace (máx. 5 por correo en ventana móvil de 24 h) con respuesta uniforme.

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from app.shared.domain.contracts import IAccountRepository, IClock, IEmailSender, ITokenService

from .request import ActivarCuentaRequest, MensajeResponse, ReenviarActivacionRequest


class ActivarCuentaHandler:
    def __init__(self, cuentas: IAccountRepository, tokens: ITokenService, correo: IEmailSender, clock: IClock) -> None:
        self._cuentas = cuentas
        self._tokens = tokens
        self._correo = correo
        self._clock = clock

    async def handle(self, body: ActivarCuentaRequest) -> MensajeResponse:
        """Ejecuta el caso de uso."""
        raise NotImplementedError

    async def reenviar(self, body: ReenviarActivacionRequest) -> MensajeResponse:
        """Ejecuta el caso de uso."""
        raise NotImplementedError
