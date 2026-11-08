"""CU-01 — Registrar cuenta."""
import asyncio
from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.features.m01_acceso.cu01_registrar_cuenta.handler import RegistrarCuentaHandler
from app.features.m01_acceso.cu01_registrar_cuenta.request import RegistrarCuentaRequest
from app.shared.domain.entities import EstadoCuenta
from app.shared.domain.errors import Conflicto, ErrorValidacion
from tests.fakes import (FakeAccountRepository, FakeClock, FakeConfig, FakeEmailSender, FakePasswordHasher,
                         SecureTokenService, estudiante)


def _req(**kw):
    datos = dict(correo=" Ana@UNAS.edu.pe ", contrasena="clave123", confirmacion="clave123",
                 nickname="ana_07", acepta_terminos=True)
    datos.update(kw)
    return RegistrarCuentaRequest(**datos)


def _handler(repo=None, reloj=None):
    repo, correo, reloj = repo or FakeAccountRepository(), FakeEmailSender(), reloj or FakeClock()
    h = RegistrarCuentaHandler(repo, FakePasswordHasher(), SecureTokenService(), correo, FakeConfig(), reloj,
                               "https://banca.test/", "1.0")
    return h, repo, correo, reloj


def test_registro_crea_cuenta_pendiente_y_envia_enlace():
    h, repo, correo, reloj = _handler()
    respuesta = asyncio.run(h.handle(_req()))
    assert respuesta.mensaje == "Revisa tu correo para activar tu cuenta"
    cuenta = next(iter(repo.cuentas.values()))
    assert cuenta.correo_institucional == "ana@unas.edu.pe"  # RF-AUT-07: minúsculas
    assert cuenta.estado is EstadoCuenta.PENDIENTE_ACTIVACION
    assert cuenta.password_hash != "clave123"  # solo hash
    assert cuenta.aceptacion.version == "1.0" and cuenta.aceptacion.fecha == reloj.ahora()  # RF-AUT-17
    assert cuenta.activacion.expira_en == reloj.ahora() + timedelta(hours=24)
    assert cuenta.activacion.envios == 1 and not repo.sesiones  # sin sesión (RF-AUT-41)
    enviado = correo.enviados[0]
    assert enviado.enlace.startswith("https://banca.test/activar?token=") and "ana_07" in enviado.cuerpo
    token = enviado.enlace.split("token=")[1]
    assert cuenta.activacion.token_hash == SecureTokenService().hash(token) != token
    assert "correo" not in respuesta.model_dump()


def test_rechaza_otro_dominio_y_subdominio():
    h, *_ = _handler()
    for correo in ("ana@gmail.com", "ana@fiis.unas.edu.pe"):
        with pytest.raises(ErrorValidacion, match=r"Debes usar tu correo institucional \(@unas.edu.pe\)"):
            asyncio.run(h.handle(_req(correo=correo)))


def test_rechaza_correo_activo_o_pendiente():
    repo = FakeAccountRepository()
    asyncio.run(repo.crear(estudiante()))
    pendiente = estudiante(correo="beto@unas.edu.pe", nickname="beto", estado=EstadoCuenta.PENDIENTE_ACTIVACION)
    asyncio.run(repo.crear(pendiente))
    h, *_ = _handler(repo, FakeClock(pendiente.fecha_registro + timedelta(hours=71)))
    with pytest.raises(Conflicto, match="Este correo ya tiene una cuenta. Inicia sesión"):
        asyncio.run(h.handle(_req(correo="ANA@unas.edu.pe", nickname="otro")))
    with pytest.raises(Conflicto, match="pendiente de activación"):
        asyncio.run(h.handle(_req(correo="beto@unas.edu.pe", nickname="otro")))


def test_pendiente_vencida_libera_correo_y_nickname():
    repo = FakeAccountRepository()
    vieja = estudiante(nickname="ana_07", estado=EstadoCuenta.PENDIENTE_ACTIVACION)
    asyncio.run(repo.crear(vieja))
    h, *_ = _handler(repo, FakeClock(vieja.fecha_registro + timedelta(hours=72)))
    asyncio.run(h.handle(_req()))  # EA-07 al consultar
    assert len(repo.cuentas) == 1


def test_nickname_ocupado_sin_distinguir_mayusculas():
    repo = FakeAccountRepository()
    asyncio.run(repo.crear(estudiante(correo="otra@unas.edu.pe", nickname="Ana_07")))
    h, *_ = _handler(repo)
    with pytest.raises(Conflicto, match="nickname"):
        asyncio.run(h.handle(_req(nickname="ana_07")))


def test_validaciones_del_dto():
    with pytest.raises(ValidationError, match="Las contraseñas no coinciden"):
        _req(confirmacion="otra1234")
    with pytest.raises(ValidationError, match="aceptar los términos"):
        _req(acepta_terminos=False)
    with pytest.raises(ValidationError, match="obligatorio"):
        _req(nickname="")
    with pytest.raises(ValidationError, match="dígito"):
        _req(contrasena="soloLetras", confirmacion="soloLetras")


def test_fallo_al_enviar_correo_deja_cuenta_pendiente():
    h, repo, correo, _ = _handler()

    async def falla(*_):
        raise ConnectionError("smtp caído")

    correo.enviar_activacion = falla
    assert asyncio.run(h.handle(_req())).mensaje.startswith("Revisa tu correo")
    assert len(repo.cuentas) == 1
