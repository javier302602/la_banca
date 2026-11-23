"""CU-17 — Activar la cuenta con el código de 6 dígitos (+ reenvío del código)."""
import asyncio
from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.features.m01_acceso.cu17_activar_cuenta.handler import MSG_REENVIO, ActivarCuentaHandler
from app.features.m01_acceso.cu17_activar_cuenta.request import ActivarCuentaRequest, ReenviarActivacionRequest
from app.shared.domain.entities import EnlaceUnUso, EstadoCuenta
from app.shared.domain.errors import ErrorValidacion, NoDisponible
from tests.fakes import FakeAccountRepository, FakeClock, FakeEmailSender, SecureTokenService, estudiante

TOKENS = SecureTokenService()
CORREO = "ana@unas.edu.pe"


def _escenario(envios=1):
    repo, reloj, correo = FakeAccountRepository(), FakeClock(), FakeEmailSender()
    codigo, hash_ = TOKENS.generar_codigo()
    ahora = reloj.ahora()
    cuenta = estudiante(estado=EstadoCuenta.PENDIENTE_ACTIVACION, fecha=ahora,
                        activacion=EnlaceUnUso(hash_, ahora + timedelta(minutes=10),
                                               [ahora - timedelta(minutes=i) for i in range(envios)]))
    cid = asyncio.run(repo.crear(cuenta))
    return ActivarCuentaHandler(repo, TOKENS, correo, reloj), repo, reloj, correo, codigo, cid


def _activar(h, codigo, correo=CORREO):
    return asyncio.run(h.handle(ActivarCuentaRequest(correo=correo, codigo=codigo)))


def _otro(codigo):
    return f"{(int(codigo) + 1) % 1_000_000:06d}"


def test_activa_con_codigo_correcto_una_sola_vez():
    h, repo, _, _, codigo, cid = _escenario()
    assert _activar(h, codigo).mensaje == "Activación de cuenta exitosa. Pulsa Continuar para iniciar sesión"
    assert repo.cuentas[cid].estado is EstadoCuenta.ACTIVA
    with pytest.raises(NoDisponible, match="El código no es válido"):
        _activar(h, codigo)


def test_codigo_vence_a_los_10_minutos():
    h, _, reloj, _, codigo, _ = _escenario()
    reloj.avanzar(minutes=10)
    with pytest.raises(NoDisponible, match="El código venció"):
        _activar(h, codigo)


def test_maximo_5_intentos():
    h, repo, _, _, codigo, cid = _escenario()
    for restantes in (4, 3, 2, 1):
        with pytest.raises(ErrorValidacion, match=f"Te quedan {restantes} intento"):
            _activar(h, _otro(codigo))
    with pytest.raises(NoDisponible, match="Agotaste los 5 intentos"):
        _activar(h, _otro(codigo))
    with pytest.raises(NoDisponible, match="Agotaste los 5 intentos"):
        _activar(h, codigo)  # ni el código correcto sirve ya
    assert repo.cuentas[cid].estado is EstadoCuenta.PENDIENTE_ACTIVACION


def test_correo_sin_cuenta_pendiente():
    h, *_ , codigo, _ = _escenario()
    with pytest.raises(NoDisponible, match="El código no es válido"):
        _activar(h, codigo, correo="nadie@unas.edu.pe")


def test_codigo_debe_tener_6_digitos():
    for malo in ("12345", "1234567", "12a456", "１２３４５６"):
        with pytest.raises(ValidationError):
            ActivarCuentaRequest(correo=CORREO, codigo=malo)
    assert ActivarCuentaRequest(correo=CORREO, codigo=" 123 456 ").codigo == "123456"


def test_reenvio_invalida_codigo_anterior_y_reinicia_intentos():
    h, repo, _, correo, codigo, cid = _escenario()
    with pytest.raises(ErrorValidacion):
        _activar(h, _otro(codigo))
    assert asyncio.run(h.reenviar(ReenviarActivacionRequest(correo="Ana@unas.edu.pe"))).mensaje == MSG_REENVIO
    nuevo = correo.enviados[-1].codigo
    assert repo.cuentas[cid].activacion.intentos == 0
    if nuevo != codigo:
        with pytest.raises(ErrorValidacion):
            _activar(h, codigo)
    _activar(h, nuevo)
    assert repo.cuentas[cid].estado is EstadoCuenta.ACTIVA


def test_reenvio_limite_5_en_24h_con_mismo_mensaje():
    h, _, reloj, correo, *_ = _escenario(envios=5)
    assert asyncio.run(h.reenviar(ReenviarActivacionRequest(correo=CORREO))).mensaje == MSG_REENVIO
    assert correo.enviados == []
    reloj.avanzar(hours=24)  # ventana móvil: los envíos antiguos salen de la ventana
    asyncio.run(h.reenviar(ReenviarActivacionRequest(correo=CORREO)))
    assert len(correo.enviados) == 1


def test_reenvio_misma_respuesta_si_no_hay_cuenta_pendiente():
    h, _, _, correo, codigo, _ = _escenario()
    _activar(h, codigo)
    for direccion in (CORREO, "nadie@unas.edu.pe"):
        assert asyncio.run(h.reenviar(ReenviarActivacionRequest(correo=direccion))).mensaje == MSG_REENVIO
    assert correo.enviados == []
