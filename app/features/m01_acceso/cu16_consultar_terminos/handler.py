"""CU-16 — Consultar términos de uso y política de privacidad. Caso de uso (handler).

RF: RF-AUT-18, RF-AUT-24
Accesible con o sin sesión; desde el registro se consulta sin perder los datos ingresados (CU-01 A9).

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from app.shared.domain.contracts import IConfigurationProvider

from .request import TerminosResponse


class ConsultarTerminosHandler:
    def __init__(self, config: IConfigurationProvider) -> None:
        self._config = config

    async def handle(self) -> TerminosResponse:
        """Ejecuta el caso de uso."""
        raise NotImplementedError
