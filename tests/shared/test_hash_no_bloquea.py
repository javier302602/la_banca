"""bcrypt se ejecuta en un hilo (asyncio.to_thread): mientras se calcula un hash, el servidor sigue atendiendo."""
import asyncio
import time

import pytest

from app.features.m01_acceso.cu01_registrar_cuenta.handler import RegistrarCuentaHandler
from app.features.m01_acceso.cu01_registrar_cuenta.request import RegistrarCuentaRequest
from app.features.m01_acceso.cu02_iniciar_sesion.handler import IniciarSesionHandler
from app.features.m01_acceso.cu02_iniciar_sesion.request import IniciarSesionRequest
from app.features.m01_acceso.cu18_recuperar_contrasena.handler import RecuperarContrasenaHandler
from app.features.m01_acceso.cu18_recuperar_contrasena.request import (RestablecerContrasenaRequest,
                                                                      SolicitarRecuperacionRequest)
from app.shared.security.hashing import BcryptPasswordHasher, SecureTokenService
from tests.fakes import FakeAccountRepository, FakeClock, FakeConfig, FakeEmailSender, FakePasswordHasher, estudiante

DEMORA = 0.3  # s que tarda cada hash o verificación simulados


class HasherLento(FakePasswordHasher):
    """Como bcrypt: trabajo síncrono que ocupa el hilo que lo ejecuta."""

    def hash(self, contrasena):
        time.sleep(DEMORA)
        return super().hash(contrasena)

    def verificar(self, contrasena, hash_guardado):
        time.sleep(DEMORA)
        return super().verificar(contrasena, hash_guardado)


async def _ticks_durante(corrutina) -> tuple[int, object]:
    """Ejecuta `corrutina` junto a un contador que avanza cada 10 ms; devuelve cuántas veces avanzó."""
    ticks, fin = 0, asyncio.Event()

    async def contar():
        nonlocal ticks
        while not fin.is_set():
            await asyncio.sleep(0.01)
            ticks += 1

    contador = asyncio.create_task(contar())
    try:
        resultado = await corrutina
    finally:
        fin.set()
        await contador
    return ticks, resultado


def _sin_bloqueo(ticks: int, esperas: int = 1) -> None:
    # bloqueando, el contador no avanza mientras dura el hash (≈ 0 ticks); en un hilo avanza ~30 por espera
    assert ticks >= 10 * esperas, f"el event loop quedó bloqueado ({ticks} ticks)"


def test_registro_no_bloquea():
    h = RegistrarCuentaHandler(FakeAccountRepository(), HasherLento(), SecureTokenService(), FakeEmailSender(),
                               FakeConfig(), FakeClock(), "https://banca.test", "1.0")
    req = RegistrarCuentaRequest(correo="ana@unas.edu.pe", contrasena="clave123", confirmacion="clave123",
                                 nickname="ana_07", acepta_terminos=True)
    ticks, r = asyncio.run(_ticks_durante(h.handle(req)))
    assert r.mensaje == "Revisa tu correo para activar tu cuenta"
    _sin_bloqueo(ticks)


@pytest.mark.parametrize("correo", ["ana@unas.edu.pe", "nadie@unas.edu.pe"])  # con cuenta y con hash señuelo
def test_inicio_de_sesion_no_bloquea(correo):
    hasher, repo = HasherLento(), FakeAccountRepository()
    asyncio.run(repo.crear(estudiante(password_hash=FakePasswordHasher().hash("clave123"))))
    h = IniciarSesionHandler(repo, hasher, SecureTokenService(), FakeConfig(), FakeClock())
    ticks, _ = asyncio.run(_ticks_durante(_intentar(h, correo)))
    _sin_bloqueo(ticks)


async def _intentar(h, correo):
    try:
        return await h.handle(IniciarSesionRequest(correo=correo, contrasena="clave123"))
    except Exception as error:  # el correo sin cuenta falla con «Correo o contraseña incorrectos»
        return error


def test_restablecer_contrasena_no_bloquea():
    repo, correo, reloj = FakeAccountRepository(), FakeEmailSender(), FakeClock()
    asyncio.run(repo.crear(estudiante()))
    h = RecuperarContrasenaHandler(repo, SecureTokenService(), HasherLento(), correo, reloj, "https://banca.test")
    asyncio.run(h.handle(SolicitarRecuperacionRequest(correo="ana@unas.edu.pe")))
    token = correo.enviados[-1].enlace.split("token=")[1]
    req = RestablecerContrasenaRequest(token=token, contrasena="nueva1234", confirmacion="nueva1234")
    ticks, r = asyncio.run(_ticks_durante(h.restablecer(req)))
    assert r.mensaje == "Contraseña actualizada. Ya puedes iniciar sesión"
    _sin_bloqueo(ticks)


def test_bcrypt_real_por_hilo():
    hasher = BcryptPasswordHasher(costo=4)
    guardado = asyncio.run(hasher.hash_async("clave123"))
    assert asyncio.run(hasher.verificar_async("clave123", guardado))
    assert not asyncio.run(hasher.verificar_async("otra1234", guardado))
