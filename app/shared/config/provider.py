"""IConfigurationProvider desde variables de entorno (CU-15, RF-CFG-01–12, RNF-MAN-01).

- Los valores se leen en cada consulta: un cambio aplica a las operaciones posteriores (RF-CFG-10).
- Un valor fuera de rango o mal formado no se aplica: se conserva el último válido (o el valor inicial
  del SRS) y se deja constancia en el registro técnico (RF-CFG-09).
- DOMINIO_INSTITUCIONAL no tiene valor inicial en el SRS: si nunca hubo un valor válido, se lanza error.
"""
import logging
import os
from collections.abc import Mapping
from datetime import datetime

from app.shared.clock import get_clock
from app.shared.domain.contracts import IClock, IConfigurationProvider
from app.shared.domain.entities import ClaveParametro, ParametroSistema
from app.shared.domain.reglas import CATALOGO_PARAMETROS, validar_parametro

log = logging.getLogger("la_banca.config")


class ConfiguracionFaltante(RuntimeError):
    pass


class EnvConfigurationProvider(IConfigurationProvider):
    def __init__(self, entorno: Mapping[str, str] | None = None, clock: IClock | None = None) -> None:
        self._entorno = entorno if entorno is not None else os.environ
        self._clock = clock or get_clock()
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
            fecha = previo[1] if previo and previo[0] == valor else self._clock.ahora()
            self._ultimo_valido[clave] = (valor, fecha)
        elif clave in self._ultimo_valido:
            valor, fecha = self._ultimo_valido[clave]
        elif definicion.valor_inicial is not None:
            valor, fecha = definicion.valor_inicial, self._clock.ahora()
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


class ConfiguracionInvalida(RuntimeError):
    pass


def verificar_entorno(entorno: Mapping[str, str] | None = None) -> None:
    """Con ENTORNO=produccion exige proveedores reales: impide arrancar con imágenes en memoria o correo en consola."""
    entorno = entorno if entorno is not None else os.environ
    if (entorno.get("ENTORNO") or "").strip().lower() != "produccion":
        return
    errores = []
    imagenes = (entorno.get("IMAGE_STORAGE") or "memoria").strip().lower()
    if imagenes != "s3":
        errores.append(f"IMAGE_STORAGE={imagenes} no está permitido en producción (las imágenes se perderían): "
                       "usa IMAGE_STORAGE=s3")
    correo = (entorno.get("EMAIL_SENDER") or "consola").strip().lower()
    if correo != "smtp":
        errores.append(f"EMAIL_SENDER={correo} no está permitido en producción (no se enviarían los enlaces): "
                       "usa EMAIL_SENDER=smtp")
    if correo == "smtp" and (entorno.get("SMTP_TLS") or "starttls").strip().lower() == "ninguno":
        errores.append("SMTP_TLS=ninguno no está permitido en producción: usa starttls o ssl")
    # RN-31 / RNF-LEG-01–03: la política publicada debe tener versión, fecha y canal ARCO
    for nombre in ("TERMINOS_VERSION", "TERMINOS_FECHA", "CANAL_ARCO"):
        if not (entorno.get(nombre) or "").strip():
            errores.append(f"Falta {nombre}: la política de privacidad no puede publicarse sin ese dato")
    if errores:
        raise ConfiguracionInvalida("Configuración inválida para ENTORNO=produccion:\n- " + "\n- ".join(errores))
