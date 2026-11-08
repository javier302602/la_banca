"""CU-17 — Activar la cuenta (+ reenvío del enlace)."""
import asyncio
from datetime import timedelta

import pytest

from app.features.m01_acceso.cu17_activar_cuenta.handler import MSG_REENVIO, ActivarCuentaHandler
from app.features.m01_acceso.cu17_activar_cuenta.request import ActivarCuentaRequest, ReenviarActivacionRequest
from app.shared.domain.entities import EnlaceUnUso, EstadoCuenta
from app.shared.domain.errors import NoDisponible
from tests.fakes import FakeAccountRepository, FakeClock, FakeEmailSender, SecureTokenService, estudiante

TOKENS = SecureTokenService()


def _escenario(envios=1):
    repo, reloj, correo = FakeAccountRepository(), FakeClock(), FakeEmailSender()
    plano, hash_ = TOKENS.generar()
    ahora = reloj.ahora()
    cuenta = estudiante(estado=EstadoCuenta.PENDIENTE_ACTIVACION, fecha=ahora,
                        activacion=EnlaceUnUso(hash_, ahora + timedelta(hours=24),
                                               [ahora - timedelta(minutes=i) for i in range(envios)]))
    cid = asyncio.run(repo.crear(cuenta))
    return ActivarCuentaHandler(repo, TOKENS, correo, reloj, "https://banca.test"), repo, reloj, correo, plano, cid


def _activar(h, token):
    return asyncio.run(h.handle(ActivarCuentaRequest(token=token)))


def test_activa_con_enlace_vigente_una_sola_vez():
    h, repo, _, _, plano, cid = _escenario()
    assert _activar(h, plano).mensaje == "Activación de cuenta exitosa. Pulsa Continuar para iniciar sesión"
    assert repo.cuentas[cid].estado is EstadoCuenta.ACTIVA
    with pytest.raises(NoDisponible, match="El enlace de activación no es válido o ya venció"):
        _activar(h, plano)  # RNF-SEG-09


def test_rechaza_enlace_vencido_o_inexistente():
    h, _, reloj, _, plano, _ = _escenario()
    with pytest.raises(NoDisponible):
        _activar(h, "inexistente")
    reloj.avanzar(hours=24)
    with pytest.raises(NoDisponible):
        _activar(h, plano)


def test_reenvio_invalida_enlace_anterior():
    h, repo, _, correo, plano, cid = _escenario()
    assert asyncio.run(h.reenviar(ReenviarActivacionRequest(correo="Ana@unas.edu.pe"))).mensaje == MSG_REENVIO
    nuevo = correo.enviados[-1].enlace.split("token=")[1]
    with pytest.raises(NoDisponible):
        _activar(h, plano)  # RF-AUT-46
    _activar(h, nuevo)
    assert repo.cuentas[cid].estado is EstadoCuenta.ACTIVA


def test_reenvio_limite_5_en_24h_con_mismo_mensaje():
    h, _, reloj, correo, *_ = _escenario(envios=5)
    assert asyncio.run(h.reenviar(ReenviarActivacionRequest(correo="ana@unas.edu.pe"))).mensaje == MSG_REENVIO
    assert correo.enviados == []  # RF-AUT-33
    reloj.avanzar(hours=24)  # ventana móvil: los envíos antiguos salen de la ventana
    asyncio.run(h.reenviar(ReenviarActivacionRequest(correo="ana@unas.edu.pe")))
    assert len(correo.enviados) == 1


def test_reenvio_misma_respuesta_si_no_hay_cuenta_pendiente():
    h, _, _, correo, plano, _ = _escenario()
    _activar(h, plano)
    for direccion in ("ana@unas.edu.pe", "nadie@unas.edu.pe"):
        assert asyncio.run(h.reenviar(ReenviarActivacionRequest(correo=direccion))).mensaje == MSG_REENVIO
    assert correo.enviados == []
