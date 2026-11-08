"""CU-16 — Consultar términos de uso y política de privacidad. Caso de uso (handler).

RF: RF-AUT-18, RF-AUT-24 · RN-31 · RNF-LEG-02, RNF-LEG-03
Accesible con o sin sesión. Devuelve el texto vigente con su número de versión y fecha. El canal para
ejercer los derechos ARCO es configuración técnica (CANAL_ARCO) y se inserta en el texto.
"""
from collections.abc import Callable

from .request import TerminosResponse

PENDIENTE = "pendiente"
MARCA_CANAL_ARCO = "{{CANAL_ARCO}}"
CANAL_SIN_CONFIGURAR = "el canal que publique la institución (pendiente de configurar)"


class ConsultarTerminosHandler:
    def __init__(self, version: str | None, fecha: str | None, leer_texto: Callable[[], str],
                 canal_arco: str | None = None) -> None:
        self._version = version or PENDIENTE
        self._fecha = fecha or PENDIENTE
        self._leer_texto = leer_texto
        self._canal_arco = (canal_arco or "").strip() or CANAL_SIN_CONFIGURAR

    async def handle(self) -> TerminosResponse:
        texto = self._leer_texto().replace(MARCA_CANAL_ARCO, self._canal_arco)
        return TerminosResponse(version=self._version, fecha=self._fecha, texto=texto)
