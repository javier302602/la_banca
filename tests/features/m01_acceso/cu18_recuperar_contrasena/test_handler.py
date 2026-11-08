"""CU-18 — Recuperar la contraseña."""
import asyncio
from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.features.m01_acceso.cu18_recuperar_contrasena.handler import MSG_SOLICITUD, RecuperarContrasenaHandler
from app.features.m01_acceso.cu18_recuperar_contrasena.request import (RestablecerContrasenaRequest,
                                                                       SolicitarRecuperacionRequest)
from app.shared.domain.entities import EstadoCuenta, EstadoSesion, Sesion
from app.shared.domain.errors import NoDisponible
from tests.fakes import (FakeAccountRepository, FakeClock, FakeEmailSender, FakePasswordHasher,
                         SecureTokenService, estudiante)

TOKENS, HASHER = SecureTokenService(), FakePasswordHasher()


def _escenario(**kw):
    repo, reloj, correo = FakeAccountRepository(), FakeClock(), FakeEmailSender()
    cid = asyncio.run(repo.crear(estudiante(**kw)))
    h = RecuperarContrasenaHandler(repo, TOKENS, HASHER, correo, reloj, "https://banca.test")
    return h, repo, reloj, correo, cid


def _solicitar(h, correo="ana@unas.edu.pe"):
    return asyncio.run(h.handle(SolicitarRecuperacionRequest(correo=correo)))


def _restablecer(h, token, clave="nueva1234"):
    return asyncio.run(h.restablecer(RestablecerContrasenaRequest(token=token, contrasena=clave,
                                                                  confirmacion=clave)))


def test_flujo_completo_cierra_todas_las_sesiones():
    h, repo, reloj, correo, cid = _escenario()
    ahora = reloj.ahora()
    for _ in range(2):
        asyncio.run(repo.crear_sesion(Sesion("", cid, TOKENS.generar()[1], ahora, ahora,
                                             ahora + timedelta(hours=12))))
    assert _solicitar(h).mensaje == MSG_SOLICITUD
    token = correo.enviados[0].enlace.split("restablecer?token=")[1]
    assert _restablecer(h, token).mensaje == "Contraseña actualizada. Ya puedes iniciar sesión"
    assert HASHER.verificar("nueva1234", repo.cuentas[cid].password_hash)
    assert all(s.estado is EstadoSesion.CLOSED for s in repo.sesiones.values())  # RF-AUT-39
    with pytest.raises(NoDisponible, match="El enlace no es válido o ya venció"):
        _restablecer(h, token)  # un solo uso


def test_enlace_vence_a_los_30_minutos():
    h, _, reloj, correo, _ = _escenario()
    _solicitar(h)
    token = correo.enviados[0].enlace.split("token=")[1]
    reloj.avanzar(minutes=30)
    with pytest.raises(NoDisponible):
        _restablecer(h, token)


def test_respuesta_uniforme_sin_cuenta_o_cuenta_pendiente():
    h, _, _, correo, _ = _escenario(estado=EstadoCuenta.PENDIENTE_ACTIVACION)
    assert _solicitar(h).mensaje == _solicitar(h, "nadie@unas.edu.pe").mensaje == MSG_SOLICITUD
    assert correo.enviados == []


def test_nuevo_enlace_invalida_el_anterior_y_limite_5():
    h, _, _, correo, _ = _escenario()
    for _ in range(6):
        _solicitar(h)
    assert len(correo.enviados) == 5  # RF-AUT-49
    primero = correo.enviados[0].enlace.split("token=")[1]
    with pytest.raises(NoDisponible):
        _restablecer(h, primero)  # RF-AUT-50
    _restablecer(h, correo.enviados[-1].enlace.split("token=")[1])


def test_valida_nueva_contrasena():
    with pytest.raises(ValidationError, match="no coinciden"):
        RestablecerContrasenaRequest(token="t", contrasena="nueva1234", confirmacion="nueva12345")
    with pytest.raises(ValidationError, match="8 a 64"):
        RestablecerContrasenaRequest(token="t", contrasena="a1", confirmacion="a1")
