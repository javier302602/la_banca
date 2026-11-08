"""Dependencias FastAPI de sesión.

EA-01 — Cerrar sesión por inactividad (RF-AUT-11, RF-AUT-12, RF-AUT-20, RF-AUT-23, RF-AUT-25):
cada solicitud autenticada compara la hora actual con `fecha_expiracion` de la sesión; si venció,
la marca EXPIRED y responde «Tu sesión se cerró por inactividad». Si sigue vigente y la solicitud es
una interacción del usuario, reinicia el conteo (ultima_interaccion + CFG_HORAS_INACTIVIDAD_SESION).
Las actualizaciones automáticas en segundo plano envían la cabecera `X-Actualizacion-Automatica: 1`
y no reinician el conteo (RF-AUT-25).

Cookie: identificador de 256 bits, HttpOnly, Secure y SameSite=Lax (RNF-SEG-06, PA-29). En el
servidor solo se guarda su SHA-256.
"""
from dataclasses import dataclass
from datetime import timedelta

from fastapi import Depends, Request, Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.clock import get_clock
from app.shared.config.provider import get_config, variable
from app.shared.db.mapeo import doc_a_estudiante, doc_a_sesion
from app.shared.db.mongo import get_database, oid
from app.shared.domain.contracts import IAccountRepository, IClock, IConfigurationProvider
from app.shared.domain.entities import ClaveParametro, EstadoCuenta, EstadoSesion, Estudiante, Sesion
from app.shared.domain.errors import NoAutenticado
from app.shared.security.hashing import SecureTokenService

COOKIE_SESION = "la_banca_sesion"
HEADER_AUTOMATICA = "X-Actualizacion-Automatica"
MENSAJE_SIN_SESION = "Inicia sesión para continuar"
MENSAJE_INACTIVIDAD = "Tu sesión se cerró por inactividad"  # RF-AUT-23


@dataclass(frozen=True)
class SesionActual:
    sesion_id: str
    estudiante_id: str
    nickname: str


def vencimiento_sesion(config: IConfigurationProvider, ahora):
    return ahora + timedelta(hours=config.entero(ClaveParametro.HORAS_INACTIVIDAD_SESION))


class ValidadorSesion:
    def __init__(self, cuentas: IAccountRepository, config: IConfigurationProvider, clock: IClock) -> None:
        self._cuentas, self._config, self._clock = cuentas, config, clock
        self._tokens = SecureTokenService()

    async def validar(self, token: str | None, es_interaccion: bool = True) -> SesionActual:
        if not token:
            raise NoAutenticado(MENSAJE_SIN_SESION, codigo="sin_sesion")
        sesion = await self._cuentas.buscar_sesion_por_token(self._tokens.hash(token))
        if sesion is None or sesion.estado is EstadoSesion.CLOSED:
            raise NoAutenticado(MENSAJE_SIN_SESION, codigo="sin_sesion")
        ahora = self._clock.ahora()
        if sesion.estado is EstadoSesion.EXPIRED or ahora >= sesion.fecha_expiracion:
            if sesion.estado is EstadoSesion.ACTIVE:
                await self._cuentas.finalizar_sesion(sesion.id, EstadoSesion.EXPIRED, ahora)
            raise NoAutenticado(MENSAJE_INACTIVIDAD, codigo="sesion_expirada")
        estudiante = await self._cuentas.buscar_por_id(sesion.estudiante_id)
        if estudiante is None or estudiante.estado is not EstadoCuenta.ACTIVA:
            raise NoAutenticado(MENSAJE_SIN_SESION, codigo="sin_sesion")
        if es_interaccion:
            # RF-CFG-11: la nueva duración se aplica desde la siguiente interacción
            await self._cuentas.registrar_interaccion(sesion.id, ahora, vencimiento_sesion(self._config, ahora))
        return SesionActual(sesion.id, estudiante.id, estudiante.nickname)


class MongoSesionRepository(IAccountRepository):
    """Subconjunto de IAccountRepository que necesita la validación de sesión."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def buscar_sesion_por_token(self, token_hash: str) -> Sesion | None:
        doc = await self._db.sessions.find_one({"tokenHash": token_hash})
        return doc_a_sesion(doc) if doc else None

    async def buscar_por_id(self, estudiante_id: str) -> Estudiante | None:
        doc = await self._db.accounts.find_one({"_id": oid(estudiante_id)}) if oid(estudiante_id) else None
        return doc_a_estudiante(doc) if doc else None

    async def registrar_interaccion(self, sesion_id, ahora, expira_en) -> None:
        await self._db.sessions.update_one({"_id": oid(sesion_id), "status": EstadoSesion.ACTIVE.value},
                                           {"$set": {"lastInteractionAt": ahora, "expiresAt": expira_en}})

    async def finalizar_sesion(self, sesion_id, estado, ahora) -> None:
        await self._db.sessions.update_one({"_id": oid(sesion_id), "status": EstadoSesion.ACTIVE.value},
                                           {"$set": {"status": estado.value, "closedAt": ahora}})


def _validador(db: AsyncIOMotorDatabase) -> ValidadorSesion:
    return ValidadorSesion(MongoSesionRepository(db), get_config(), get_clock())


async def get_sesion_actual(request: Request, db: AsyncIOMotorDatabase = Depends(get_database)) -> SesionActual:
    """Dependencia para la API: exige sesión activa (RNF-SEG-01)."""
    es_interaccion = request.headers.get(HEADER_AUTOMATICA) != "1"
    return await _validador(db).validar(request.cookies.get(COOKIE_SESION), es_interaccion)


async def get_sesion_opcional(request: Request,
                              db: AsyncIOMotorDatabase = Depends(get_database)) -> SesionActual | None:
    """Dependencia para páginas: None si no hay sesión válida (la página redirige al inicio de sesión)."""
    try:
        return await _validador(db).validar(request.cookies.get(COOKIE_SESION), True)
    except NoAutenticado as error:
        request.state.motivo_sin_sesion = error.codigo
        return None


def escribir_cookie_sesion(response: Response, token: str) -> None:
    response.set_cookie(COOKIE_SESION, token, httponly=True, samesite="lax", path="/",
                        secure=variable("COOKIE_SECURE", "true") != "false")


def borrar_cookie_sesion(response: Response) -> None:
    response.delete_cookie(COOKIE_SESION, path="/", httponly=True, samesite="lax",
                           secure=variable("COOKIE_SECURE", "true") != "false")
