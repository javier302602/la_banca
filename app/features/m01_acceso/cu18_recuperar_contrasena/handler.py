"""CU-18 — Recuperar la contraseña. Caso de uso (handler).

RF: RF-AUT-35–39, RF-AUT-48–50
- Solicitud: respuesta uniforme (RN-47); solo una cuenta activada recibe enlace (RN-46); máximo 5 enlaces
  en cualquier ventana de 24 h (RF-AUT-49); un enlace nuevo invalida el anterior (RF-AUT-50).
- Restablecer: token de un solo uso con vigencia de 30 min; al usarlo se cierran todas las sesiones (RF-AUT-39).
"""
import logging

from app.shared.domain.contracts import IAccountRepository, IClock, IEmailSender, IPasswordHasher, ITokenService
from app.shared.domain.entities import (
    MAX_ENLACES_24H,
    VENTANA_ENLACES,
    VIGENCIA_ENLACE_RECUPERACION,
    EnlaceUnUso,
    EstadoCuenta,
    PropositoEnlace,
)
from app.shared.domain.errors import NoDisponible

from .request import MensajeResponse, RestablecerContrasenaRequest, SolicitarRecuperacionRequest

log = logging.getLogger("la_banca.cu18")

MSG_SOLICITUD = "Si el correo tiene una cuenta activada, recibirás un enlace para cambiar tu contraseña"  # RF-AUT-35
MSG_ENLACE_INVALIDO = "El enlace no es válido o ya venció"                                              # RF-AUT-38
MSG_ACTUALIZADA = "Contraseña actualizada. Ya puedes iniciar sesión"                                    # RF-AUT-48


class RecuperarContrasenaHandler:
    def __init__(self, cuentas: IAccountRepository, tokens: ITokenService, hasher: IPasswordHasher,
                 correo: IEmailSender, clock: IClock, url_base: str) -> None:
        self._cuentas = cuentas
        self._tokens = tokens
        self._hasher = hasher
        self._correo = correo
        self._clock = clock
        self._url_base = url_base.rstrip("/")

    async def handle(self, body: SolicitarRecuperacionRequest) -> MensajeResponse:
        ahora = self._clock.ahora()
        estudiante = await self._cuentas.buscar_por_correo(body.correo)
        if estudiante is None or estudiante.estado is not EstadoCuenta.ACTIVA:
            return MensajeResponse(mensaje=MSG_SOLICITUD)
        recientes = [t for t in estudiante.recuperacion.envios_en if t > ahora - VENTANA_ENLACES]
        if len(recientes) >= MAX_ENLACES_24H:
            return MensajeResponse(mensaje=MSG_SOLICITUD)
        token, token_hash = self._tokens.generar()
        await self._cuentas.registrar_enlace(
            estudiante.id, PropositoEnlace.RECUPERACION,
            EnlaceUnUso(token_hash, ahora + VIGENCIA_ENLACE_RECUPERACION, recientes + [ahora]))
        try:
            await self._correo.enviar_recuperacion(estudiante.correo_institucional,
                                                   f"{self._url_base}/restablecer?token={token}")
        except Exception:
            log.exception("No se pudo enviar el correo de recuperación")
        return MensajeResponse(mensaje=MSG_SOLICITUD)

    async def restablecer(self, body: RestablecerContrasenaRequest) -> MensajeResponse:
        ahora = self._clock.ahora()
        estudiante = await self._cuentas.restablecer_con_enlace(self._tokens.hash(body.token),
                                                                self._hasher.hash(body.contrasena), ahora)
        if estudiante is None:
            raise NoDisponible(MSG_ENLACE_INVALIDO, codigo="enlace_invalido")
        await self._cuentas.cerrar_sesiones_de(estudiante.id, ahora)
        return MensajeResponse(mensaje=MSG_ACTUALIZADA)
