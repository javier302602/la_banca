"""CU-02 — Iniciar sesión. Caso de uso (handler).

RF: RF-AUT-08, RF-AUT-09, RF-AUT-12, RF-AUT-19–22, RF-AUT-25, RF-AUT-30
Incluye EA-06 (Desbloquear inicio de sesión; RF-AUT-19, RF-AUT-21, RF-AUT-22) evaluado al recibir el
intento: los fallos se cuentan por correo (exista o no la cuenta, PA-27); 5 fallos consecutivos en 15 min
bloquean el correo 15 min desde el quinto; los intentos durante el bloqueo no lo prolongan.
"""
from datetime import datetime, timedelta

from app.shared.domain.contracts import IAccountRepository, IClock, IConfigurationProvider, IPasswordHasher, ITokenService
from app.shared.domain.entities import (
    VENTANA_INTENTOS_FALLIDOS,
    ClaveParametro,
    EstadoCuenta,
    IntentoAcceso,
    Sesion,
)
from app.shared.domain.errors import DemasiadosIntentos, NoAutenticado, Prohibido
from app.shared.domain.reglas import minutos_hacia_arriba

from .request import IniciarSesionRequest, SesionIniciada, SesionResponse

MSG_CREDENCIALES = "Correo o contraseña incorrectos"                                            # RF-AUT-09
MSG_NO_ACTIVADA = "Tu cuenta aún no está activada. Revisa tu correo o solicita un nuevo enlace"  # RF-AUT-30
_SEÑUELOS: dict[str, str] = {}  # un hash por proceso y tipo de hasher


class IniciarSesionHandler:
    def __init__(self, cuentas: IAccountRepository, hasher: IPasswordHasher, tokens: ITokenService,
                 config: IConfigurationProvider, clock: IClock) -> None:
        self._cuentas = cuentas
        self._hasher = hasher
        self._tokens = tokens
        self._config = config
        self._clock = clock

    async def _hash_señuelo(self) -> str:
        """Hash real para verificar aunque el correo no exista: iguala el tiempo de respuesta (RF-AUT-09)."""
        clave = type(self._hasher).__name__
        if clave not in _SEÑUELOS:
            _SEÑUELOS[clave] = await self._hasher.hash_async("señuelo-sin-cuenta-0")
        return _SEÑUELOS[clave]

    async def handle(self, body: IniciarSesionRequest) -> SesionIniciada:
        ahora = self._clock.ahora()
        intento = await self._cuentas.obtener_intento(body.correo)
        if intento is not None:
            if intento.bloqueado_hasta and ahora < intento.bloqueado_hasta:
                minutos = minutos_hacia_arriba(intento.bloqueado_hasta - ahora)
                raise DemasiadosIntentos(f"Demasiados intentos. Vuelve a intentarlo en {minutos} min",  # RF-AUT-21
                                         minutos=minutos)
            if self._evaluar_desbloqueo(intento, ahora):
                await self._cuentas.reiniciar_intentos(body.correo)
                intento = None

        estudiante = await self._cuentas.buscar_por_correo(body.correo)
        if estudiante is not None and estudiante.pendiente_vencida(ahora):
            estudiante = None  # EA-07 al consultar: la cuenta ya no existe
        guardado = estudiante.password_hash if estudiante else await self._hash_señuelo()
        valida = await self._hasher.verificar_async(body.contrasena, guardado)  # en un hilo: no bloquea el servidor
        if estudiante is None or not valida:
            await self._registrar_fallo(body.correo, intento, ahora)
            raise NoAutenticado(MSG_CREDENCIALES, codigo="credenciales_invalidas")
        if estudiante.estado is EstadoCuenta.PENDIENTE_ACTIVACION:
            raise Prohibido(MSG_NO_ACTIVADA, codigo="cuenta_no_activada")

        await self._cuentas.reiniciar_intentos(body.correo)  # RF-AUT-22
        token, token_hash = self._tokens.generar()
        horas = self._config.entero(ClaveParametro.HORAS_INACTIVIDAD_SESION)
        await self._cuentas.crear_sesion(Sesion(id="", estudiante_id=estudiante.id, token_hash=token_hash,
                                                fecha_inicio=ahora, ultima_interaccion=ahora,
                                                fecha_expiracion=ahora + timedelta(hours=horas)))
        return SesionIniciada(token=token, respuesta=SesionResponse(nickname=estudiante.nickname))

    async def _registrar_fallo(self, correo: str, intento: IntentoAcceso | None, ahora: datetime) -> None:
        if intento is None:
            intento = IntentoAcceso(correo_ingresado=correo, conteo_fallidos=0, primer_fallo=ahora, ultimo_fallo=ahora)
        intento.registrar_fallo(ahora)  # ventana móvil de 15 min; bloquea al 5.º fallo (RF-AUT-19)
        await self._cuentas.guardar_intento(intento)

    def _evaluar_desbloqueo(self, intento: IntentoAcceso, ahora: datetime) -> bool:
        """EA-06 — True si el bloqueo ya venció o si todos los fallos de la racha salieron de la ventana."""
        if intento.bloqueado_hasta is not None:
            return ahora >= intento.bloqueado_hasta
        return ahora - intento.ultimo_fallo > VENTANA_INTENTOS_FALLIDOS
