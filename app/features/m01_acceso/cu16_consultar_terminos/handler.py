"""CU-16 — Consultar términos de uso y política de privacidad. Caso de uso (handler).

RF: RF-AUT-18, RF-AUT-24
Accesible con o sin sesión. Devuelve el texto vigente con su número de versión y fecha.
"""
from collections.abc import Callable

from .request import TerminosResponse

PENDIENTE = "pendiente"


class ConsultarTerminosHandler:
    def __init__(self, version: str | None, fecha: str | None, leer_texto: Callable[[], str]) -> None:
        self._version = version or PENDIENTE
        self._fecha = fecha or PENDIENTE
        self._leer_texto = leer_texto

    async def handle(self) -> TerminosResponse:
        return TerminosResponse(version=self._version, fecha=self._fecha, texto=self._leer_texto())
