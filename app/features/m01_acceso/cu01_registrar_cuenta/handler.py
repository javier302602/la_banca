"""CU-01 — Registrar cuenta. Caso de uso (handler).

RF: RF-AUT-01–07, RF-AUT-14–17, RF-AUT-28, RF-AUT-41–43
Crea la cuenta en estado PENDIENTE_ACTIVACION (sin sesión) y envía el enlace de activación
con token de un solo uso (vigencia 24 h; cuenta como 1 de los 5 envíos permitidos en 24 h).
"""
import logging

from app.shared.domain.contracts import (
    IAccountRepository,
    IClock,
    IConfigurationProvider,
    IEmailSender,
    IPasswordHasher,
    ITokenService,
)
from app.shared.domain.entities import (
    PLAZO_CUENTA_NO_ACTIVADA,
    VIGENCIA_ENLACE_ACTIVACION,
    AceptacionTerminos,
    ClaveParametro,
    EnlaceUnUso,
    EstadoCuenta,
    Estudiante,
)
from app.shared.domain.errors import Conflicto, ErrorValidacion
from app.shared.domain.reglas import correo_del_dominio

from .request import MensajeResponse, RegistrarCuentaRequest

log = logging.getLogger("la_banca.cu01")

MSG_EXITO = "Revisa tu correo para activar tu cuenta"                        # RF-AUT-42
MSG_CORREO_REGISTRADO = "Este correo ya tiene una cuenta. Inicia sesión"      # RF-AUT-03
MSG_CORREO_PENDIENTE = "Este correo tiene una cuenta pendiente de activación"  # RF-AUT-43
MSG_NICKNAME_OCUPADO = "Ese nickname ya está en uso. Elige otro"              # RF-AUT-06


class RegistrarCuentaHandler:
    def __init__(self, cuentas: IAccountRepository, hasher: IPasswordHasher, tokens: ITokenService,
                 correo: IEmailSender, config: IConfigurationProvider, clock: IClock,
                 url_base: str, version_terminos: str) -> None:
        self._cuentas = cuentas
        self._hasher = hasher
        self._tokens = tokens
        self._correo = correo
        self._config = config
        self._clock = clock
        self._url_base = url_base.rstrip("/")
        self._version_terminos = version_terminos

    async def handle(self, body: RegistrarCuentaRequest) -> MensajeResponse:
        ahora = self._clock.ahora()
        dominio = self._config.texto(ClaveParametro.DOMINIO_INSTITUCIONAL)
        if not correo_del_dominio(body.correo, dominio):
            raise ErrorValidacion(f"Debes usar tu correo institucional (@{dominio})", codigo="dominio_invalido")

        # EA-07 al consultar: las cuentas pendientes con más de 72 h liberan correo y nickname (RN-43)
        await self._cuentas.eliminar_no_activadas(ahora - PLAZO_CUENTA_NO_ACTIVADA)

        existente = await self._cuentas.buscar_por_correo(body.correo)
        if existente is not None:
            if existente.estado is EstadoCuenta.ACTIVA:
                raise Conflicto(MSG_CORREO_REGISTRADO, codigo="correo_registrado")
            raise Conflicto(MSG_CORREO_PENDIENTE, codigo="cuenta_pendiente")
        if await self._cuentas.existe_por_nickname(body.nickname):
            raise Conflicto(MSG_NICKNAME_OCUPADO, codigo="nickname_ocupado")

        token, token_hash = self._tokens.generar()
        estudiante = Estudiante(
            id="",
            correo_institucional=body.correo,
            password_hash=self._hasher.hash(body.contrasena),
            nickname=body.nickname,
            estado=EstadoCuenta.PENDIENTE_ACTIVACION,
            fecha_registro=ahora,
            aceptacion=AceptacionTerminos(self._version_terminos, ahora),
            activacion=EnlaceUnUso(token_hash, ahora + VIGENCIA_ENLACE_ACTIVACION, [ahora]),
        )
        try:
            await self._cuentas.crear(estudiante)
        except Conflicto as error:  # carrera con otro registro simultáneo
            if error.codigo == "nickname_duplicado":
                raise Conflicto(MSG_NICKNAME_OCUPADO, codigo="nickname_ocupado") from None
            raise Conflicto(MSG_CORREO_PENDIENTE, codigo="cuenta_pendiente") from None

        try:
            await self._correo.enviar_activacion(body.correo, body.nickname, f"{self._url_base}/activar?token={token}")
        except Exception:  # E3: la cuenta queda pendiente; se puede pedir un nuevo enlace (CU-17 A1)
            log.exception("No se pudo enviar el correo de activación")
        return MensajeResponse(mensaje=MSG_EXITO)
