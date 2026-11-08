"""IConfigurationProvider desde variables de entorno (CU-15, RF-CFG-01–12, RNF-MAN-01).

- Los valores se leen en cada consulta: un cambio aplica a las operaciones posteriores (RF-CFG-10).
- Un valor fuera de rango o mal formado no se aplica: se conserva el último válido (o el valor inicial
  del SRS) y se deja constancia en el registro técnico (RF-CFG-09).
- DOMINIO_INSTITUCIONAL no tiene valor inicial en el SRS: si nunca hubo un valor válido, se lanza error.
"""
import logging
import os
from collections.abc import Mapping
from datetime import datetime, timezone

from app.shared.domain.contracts import IConfigurationProvider
from app.shared.domain.entities import ClaveParametro, ParametroSistema
from app.shared.domain.reglas import CATALOGO_PARAMETROS, validar_parametro

log = logging.getLogger("la_banca.config")


class ConfiguracionFaltante(RuntimeError):
    pass


class EnvConfigurationProvider(IConfigurationProvider):
    def __init__(self, entorno: Mapping[str, str] | None = None) -> None:
        self._entorno = entorno if entorno is not None else os.environ
        self._ultimo_valido: dict[ClaveParametro, tuple[str | int, datetime]] = {}

    def obtener(self, clave: ClaveParametro) -> ParametroSistema:
        definicion = CATALOGO_PARAMETROS[clave]
        crudo = self._entorno.get(clave.value)
        valor: str | int | None = None
        if crudo is not None and crudo.strip() != "":
            try:
                valor = validar_parametro(clave, crudo)
            except ValueError as error:
                log.error("Parámetro rechazado, se conserva el último valor válido: %s", error)
        if valor is not None:
            previo = self._ultimo_valido.get(clave)
            fecha = previo[1] if previo and previo[0] == valor else datetime.now(timezone.utc)
            self._ultimo_valido[clave] = (valor, fecha)
        elif clave in self._ultimo_valido:
            valor, fecha = self._ultimo_valido[clave]
        elif definicion.valor_inicial is not None:
            valor, fecha = definicion.valor_inicial, datetime.now(timezone.utc)
        else:
            raise ConfiguracionFaltante(f"Falta configurar {clave.value} (RF-CFG-01)")
        return ParametroSistema(clave=clave, valor=valor, tipo_dato=definicion.tipo,
                                rango_permitido=definicion.rango, fecha_actualizacion=fecha)

    def obtener_todos(self) -> dict[ClaveParametro, ParametroSistema]:
        return {clave: self.obtener(clave) for clave in CATALOGO_PARAMETROS}


_proveedor = EnvConfigurationProvider()


def get_config() -> IConfigurationProvider:
    return _proveedor


def variable(nombre: str, por_defecto: str | None = None) -> str | None:
    """Variables técnicas que no son parámetros de negocio (URIs, credenciales, selección de proveedores)."""
    valor = os.environ.get(nombre)
    return valor if valor not in (None, "") else por_defecto
