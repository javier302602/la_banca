"""CU-15 — Configurar los parámetros del sistema. Caso de uso (handler).

RF: RF-CFG-01, RF-CFG-03, RF-CFG-05–12
Sin endpoint público ni pantalla de administración (RF-CFG-08). El responsable técnico ajusta variables de entorno; este handler valida rangos (RF-CFG-09) y conserva el último valor válido.

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from app.shared.domain.entities import ParametroSistema
from app.shared.domain.contracts import IConfigurationProvider

from .request import ParametroRequest


class ConfigurarParametrosHandler:
    def __init__(self, config: IConfigurationProvider) -> None:
        self._config = config

    async def handle(self, body: ParametroRequest) -> ParametroSistema:
        """Ejecuta el caso de uso."""
        raise NotImplementedError
