"""CU-17 — Activar la cuenta. Caso de uso (handler).

RF: RF-AUT-29, RF-AUT-31–33, RF-AUT-44–47
- Activación: el token es de un solo uso y vence a las 24 h (RN-41, RNF-SEG-09); se invalida al activar.
- A1 Reenvío: como máximo 5 enlaces por correo en cualquier ventana de 24 h, incluido el del registro
  (RF-AUT-33); emitir uno nuevo invalida el anterior (RF-AUT-46); la respuesta es siempre la misma (RF-AUT-47).
"""
import logging

from app.shared.domain.contracts import IAccountRepository, IClock, IEmailSender, ITokenService
from app.shared.domain.entities import (
    MAX_ENLACES_24H,
    PLAZO_CUENTA_NO_ACTIVADA,
    VENTANA_ENLACES,
    VIGENCIA_ENLACE_ACTIVACION,
    EnlaceUnUso,
    EstadoCuenta,
    PropositoEnlace,
)
from app.shared.domain.errors import NoDisponible

from .request import ActivarCuentaRequest, MensajeResponse, ReenviarActivacionRequest

log = logging.getLogger("la_banca.cu17")

MSG_ACTIVADA = "Activación de cuenta exitosa. Pulsa Continuar para iniciar sesión"           # RF-AUT-44
MSG_ENLACE_INVALIDO = "El enlace de activación no es válido o ya venció"                      # RF-AUT-31
MSG_REENVIO = "Si el correo tiene una cuenta pendiente, recibirás un nuevo enlace de activación"  # RF-AUT-47


class ActivarCuentaHandler:
    def __init__(self, cuentas: IAccountRepository, tokens: ITokenService, correo: IEmailSender,
                 clock: IClock, url_base: str) -> None:
        self._cuentas = cuentas
        self._tokens = tokens
        self._correo = correo
        self._clock = clock
        self._url_base = url_base.rstrip("/")

    async def handle(self, body: ActivarCuentaRequest) -> MensajeResponse:
        estudiante = await self._cuentas.activar_con_enlace(self._tokens.hash(body.token), self._clock.ahora())
        if estudiante is None:
            raise NoDisponible(MSG_ENLACE_INVALIDO, codigo="enlace_invalido")
        return MensajeResponse(mensaje=MSG_ACTIVADA)

    async def reenviar(self, body: ReenviarActivacionRequest) -> MensajeResponse:
        ahora = self._clock.ahora()
        await self._cuentas.eliminar_no_activadas(ahora - PLAZO_CUENTA_NO_ACTIVADA)  # EA-07 al consultar
        estudiante = await self._cuentas.buscar_por_correo(body.correo)
        if estudiante is None or estudiante.estado is not EstadoCuenta.PENDIENTE_ACTIVACION:
            return MensajeResponse(mensaje=MSG_REENVIO)
        recientes = [t for t in estudiante.activacion.envios_en if t > ahora - VENTANA_ENLACES]
        if len(recientes) >= MAX_ENLACES_24H:
            return MensajeResponse(mensaje=MSG_REENVIO)  # RF-AUT-33: mismo mensaje
        token, token_hash = self._tokens.generar()
        await self._cuentas.registrar_enlace(
            estudiante.id, PropositoEnlace.ACTIVACION,
            EnlaceUnUso(token_hash, ahora + VIGENCIA_ENLACE_ACTIVACION, recientes + [ahora]))
        try:
            await self._correo.enviar_activacion(estudiante.correo_institucional, estudiante.nickname,
                                                 f"{self._url_base}/activar?token={token}")
        except Exception:
            log.exception("No se pudo enviar el correo de activación")
        return MensajeResponse(mensaje=MSG_REENVIO)
