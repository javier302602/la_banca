"""CU-17 — Activar la cuenta con el código enviado al correo. Caso de uso (handler).

Flujo:
1. El estudiante escribe su correo y el código de 6 dígitos.
2. Si el código coincide, está vigente (10 min) y no agotó los 5 intentos → la cuenta pasa a ACTIVA.
3. Si no coincide → se suma un intento y se informa cuántos quedan.
A1 Reenvío: máximo 5 códigos por correo en 24 h (incluido el del registro); un código nuevo invalida el
anterior y reinicia los intentos. La respuesta del reenvío es siempre la misma (no revela si el correo existe).
"""
import logging

from app.shared.domain.contracts import IAccountRepository, IClock, IEmailSender, ITokenService
from app.shared.domain.entities import (
    MAX_ENLACES_24H,
    MAX_INTENTOS_CODIGO,
    PLAZO_CUENTA_NO_ACTIVADA,
    VENTANA_ENLACES,
    VIGENCIA_CODIGO_ACTIVACION,
    EnlaceUnUso,
    EstadoCuenta,
    PropositoEnlace,
)
from app.shared.domain.errors import ErrorValidacion, NoDisponible

from .request import ActivarCuentaRequest, MensajeResponse, ReenviarActivacionRequest

log = logging.getLogger("la_banca.cu17")

MSG_ACTIVADA = "Activación de cuenta exitosa. Pulsa Continuar para iniciar sesión"
MSG_CODIGO_INVALIDO = "El código no es válido. Pide uno nuevo"
MSG_CODIGO_VENCIDO = "El código venció. Pide uno nuevo"
MSG_SIN_INTENTOS = "Agotaste los 5 intentos. Pide un código nuevo"
MSG_REENVIO = "Si el correo tiene una cuenta pendiente, recibirás un código nuevo"


class ActivarCuentaHandler:
    def __init__(self, cuentas: IAccountRepository, tokens: ITokenService, correo: IEmailSender,
                 clock: IClock) -> None:
        self._cuentas = cuentas
        self._tokens = tokens
        self._correo = correo
        self._clock = clock

    async def handle(self, body: ActivarCuentaRequest) -> MensajeResponse:
        ahora = self._clock.ahora()
        estudiante = await self._cuentas.buscar_por_correo(body.correo)
        if (estudiante is None or estudiante.estado is not EstadoCuenta.PENDIENTE_ACTIVACION
                or estudiante.pendiente_vencida(ahora) or not estudiante.activacion.token_hash):
            raise NoDisponible(MSG_CODIGO_INVALIDO, codigo="codigo_invalido")
        codigo = estudiante.activacion
        if codigo.intentos >= MAX_INTENTOS_CODIGO:
            raise NoDisponible(MSG_SIN_INTENTOS, codigo="codigo_agotado")
        if codigo.expira_en is None or ahora >= codigo.expira_en:
            raise NoDisponible(MSG_CODIGO_VENCIDO, codigo="codigo_vencido")

        if await self._cuentas.activar_con_codigo(estudiante.id, self._tokens.hash(body.codigo), ahora):
            return MensajeResponse(mensaje=MSG_ACTIVADA)

        restantes = MAX_INTENTOS_CODIGO - await self._cuentas.sumar_intento_codigo(estudiante.id)
        if restantes <= 0:
            raise NoDisponible(MSG_SIN_INTENTOS, codigo="codigo_agotado")
        raise ErrorValidacion(f"Código incorrecto. Te quedan {restantes} intento(s)",
                              codigo="codigo_incorrecto", campo="codigo")

    async def reenviar(self, body: ReenviarActivacionRequest) -> MensajeResponse:
        ahora = self._clock.ahora()
        await self._cuentas.eliminar_no_activadas(ahora - PLAZO_CUENTA_NO_ACTIVADA)  # EA-07 al consultar
        estudiante = await self._cuentas.buscar_por_correo(body.correo)
        if estudiante is None or estudiante.estado is not EstadoCuenta.PENDIENTE_ACTIVACION:
            return MensajeResponse(mensaje=MSG_REENVIO)
        recientes = [t for t in estudiante.activacion.envios_en if t > ahora - VENTANA_ENLACES]
        if len(recientes) >= MAX_ENLACES_24H:
            return MensajeResponse(mensaje=MSG_REENVIO)  # mismo mensaje: no revela el límite
        codigo, codigo_hash = self._tokens.generar_codigo()
        await self._cuentas.registrar_enlace(  # reemplaza el código anterior y reinicia los intentos
            estudiante.id, PropositoEnlace.ACTIVACION,
            EnlaceUnUso(codigo_hash, ahora + VIGENCIA_CODIGO_ACTIVACION, recientes + [ahora]))
        try:
            await self._correo.enviar_activacion(estudiante.correo_institucional, estudiante.nickname, codigo)
        except Exception:
            log.exception("No se pudo enviar el código de activación")
        return MensajeResponse(mensaje=MSG_REENVIO)
