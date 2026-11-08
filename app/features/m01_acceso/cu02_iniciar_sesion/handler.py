"""CU-02 — Iniciar sesión. Caso de uso (handler).

RF: RF-AUT-08, RF-AUT-09, RF-AUT-12, RF-AUT-19–22, RF-AUT-25, RF-AUT-30
Incluye EA-06 (Desbloquear inicio de sesión; RF-AUT-19, RF-AUT-21, RF-AUT-22): al recibir un intento se evalúa si pasaron 15 min desde el 5.º intento fallido y, de ser así, se levanta el bloqueo y el contador vuelve a 0. Una cuenta pendiente de activación no obtiene sesión (RF-AUT-30).

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from datetime import datetime

from app.shared.domain.entities import IntentoAcceso
from app.shared.domain.contracts import IAccountRepository, IClock, IConfigurationProvider, IPasswordHasher, ITokenService

from .request import IniciarSesionRequest, SesionResponse


class IniciarSesionHandler:
    def __init__(self, cuentas: IAccountRepository, hasher: IPasswordHasher, tokens: ITokenService, config: IConfigurationProvider, clock: IClock) -> None:
        self._cuentas = cuentas
        self._hasher = hasher
        self._tokens = tokens
        self._config = config
        self._clock = clock

    async def handle(self, body: IniciarSesionRequest) -> SesionResponse:
        """Ejecuta el caso de uso."""
        raise NotImplementedError

    def _evaluar_desbloqueo(self, intento: IntentoAcceso, ahora: datetime) -> bool:
        """EA-06 — Desbloquear inicio de sesión. True si el bloqueo ya venció (15 min)."""
        raise NotImplementedError
