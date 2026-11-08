"""CU-15 — Configurar los parámetros del sistema. Caso de uso (handler).

RF: RF-CFG-01, RF-CFG-03, RF-CFG-05–12
Sin endpoint público ni pantalla de administración (RF-CFG-08). El responsable técnico cambia las
variables de entorno; este caso de uso:
- valida un valor candidato contra su tipo y rango (RF-CFG-09, CU-15 E1);
- revisa la configuración completa, informa los valores rechazados (se conserva el último válido) y
  registra los valores efectivos en system_parameters (Entregable 2, Tabla 6.8).
Los cambios solo afectan a operaciones posteriores (RF-CFG-10/11): los plazos ya calculados se guardan
con cada publicación, sesión o reporte y no se recalculan.
"""
import logging
from collections.abc import Mapping

from app.shared.domain.contracts import IClock, IConfigurationProvider, IParameterRepository
from app.shared.domain.entities import ParametroSistema
from app.shared.domain.errors import ErrorValidacion
from app.shared.domain.reglas import CATALOGO_PARAMETROS, validar_parametro

from .request import ParametroRequest, RevisionConfiguracion

log = logging.getLogger("la_banca.cu15")


class ConfigurarParametrosHandler:
    def __init__(self, config: IConfigurationProvider, parametros: IParameterRepository | None, clock: IClock) -> None:
        self._config = config
        self._parametros = parametros
        self._clock = clock

    async def handle(self, body: ParametroRequest) -> ParametroSistema:
        """Valida un valor candidato. ErrorValidacion si no se puede aplicar (CU-15 E1)."""
        definicion = CATALOGO_PARAMETROS[body.clave]
        try:
            valor = validar_parametro(body.clave, body.valor)
        except ValueError as error:
            log.error("Valor de parámetro rechazado: %s", error)
            raise ErrorValidacion(str(error), codigo="parametro_invalido") from None
        return ParametroSistema(body.clave, valor, definicion.tipo, definicion.rango, self._clock.ahora())

    async def revisar(self, entorno: Mapping[str, str], registrar: bool = False) -> RevisionConfiguracion:
        """Revisa los valores configurados y, si se pide, registra los efectivos en system_parameters."""
        rechazados = []
        for clave in CATALOGO_PARAMETROS:
            crudo = entorno.get(clave.value)
            if crudo not in (None, ""):
                try:
                    await self.handle(ParametroRequest(clave=clave, valor=crudo))
                except ErrorValidacion as error:
                    rechazados.append(error.mensaje)
        efectivos = self._config.obtener_todos()
        if registrar and self._parametros is not None:
            for parametro in efectivos.values():
                await self._parametros.guardar(parametro)
        return RevisionConfiguracion(efectivos={c.value: p.valor for c, p in efectivos.items()},
                                     rechazados=rechazados)
