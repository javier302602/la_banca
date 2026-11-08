"""CU-02 — Iniciar sesión (+ EA-06)."""
import asyncio
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.features.m01_acceso.cu02_iniciar_sesion import endpoint
from app.features.m01_acceso.cu02_iniciar_sesion.handler import IniciarSesionHandler
from app.features.m01_acceso.cu02_iniciar_sesion.request import IniciarSesionRequest
from app.shared.domain.entities import EstadoCuenta
from app.shared.domain.errors import DemasiadosIntentos, NoAutenticado, Prohibido
from tests.fakes import (FakeAccountRepository, FakeClock, FakeConfig, FakePasswordHasher, SecureTokenService,
                         estudiante)

HASHER = FakePasswordHasher()


def _escenario(**kw):
    repo, reloj = FakeAccountRepository(), FakeClock()
    asyncio.run(repo.crear(estudiante(password_hash=HASHER.hash("clave123"), **kw)))
    return IniciarSesionHandler(repo, HASHER, SecureTokenService(), FakeConfig(), reloj), repo, reloj


def _login(h, clave="clave123", correo="ANA@unas.edu.pe "):
    return asyncio.run(h.handle(IniciarSesionRequest(correo=correo, contrasena=clave)))


def test_inicio_exitoso_crea_sesion_de_12_horas():
    h, repo, reloj = _escenario()
    resultado = _login(h)
    assert resultado.respuesta.nickname == "ana_07"
    sesion = next(iter(repo.sesiones.values()))
    assert sesion.fecha_expiracion == reloj.ahora() + timedelta(hours=12)
    assert sesion.token_hash == SecureTokenService().hash(resultado.token) != resultado.token


def test_sesiones_simultaneas():
    h, repo, _ = _escenario()
    _login(h)
    _login(h)
    assert len(repo.sesiones) == 2  # RF-AUT-20


def test_mismo_mensaje_para_correo_o_clave_incorrectos():
    h, *_ = _escenario()
    for correo, clave in (("nadie@unas.edu.pe", "clave123"), ("ana@unas.edu.pe", "mala1234")):
        with pytest.raises(NoAutenticado, match="^Correo o contraseña incorrectos$"):
            _login(h, clave, correo)


def test_cuenta_pendiente_no_obtiene_sesion():
    h, repo, _ = _escenario(estado=EstadoCuenta.PENDIENTE_ACTIVACION)
    with pytest.raises(Prohibido, match="Tu cuenta aún no está activada"):
        _login(h)
    assert not repo.sesiones


def test_bloqueo_tras_5_fallos_y_desbloqueo_ea06():
    h, repo, reloj = _escenario()
    for _ in range(5):
        with pytest.raises(NoAutenticado):
            _login(h, "mala1234")
        reloj.avanzar(minutes=1)
    # bloqueado desde el 5.º fallo (minuto 4) hasta el minuto 19; ahora es el minuto 5
    with pytest.raises(DemasiadosIntentos, match="Vuelve a intentarlo en 14 min"):
        _login(h)  # aun con la clave correcta
    reloj.avanzar(minutes=13, seconds=30)
    with pytest.raises(DemasiadosIntentos, match="en 1 min"):  # los intentos no lo prolongan
        _login(h)
    reloj.avanzar(seconds=30)  # minuto 19: vence el bloqueo (EA-06)
    assert _login(h).respuesta.nickname == "ana_07"
    assert "ana@unas.edu.pe" not in repo.intentos  # RF-AUT-22


def test_bloqueo_aplica_a_correos_sin_cuenta():
    h, *_ = _escenario()
    for _ in range(5):
        with pytest.raises(NoAutenticado):
            _login(h, correo="fantasma@unas.edu.pe")
    with pytest.raises(DemasiadosIntentos):
        _login(h, correo="fantasma@unas.edu.pe")


def test_fallos_fuera_de_la_ventana_no_bloquean():
    h, repo, reloj = _escenario()
    for _ in range(4):
        with pytest.raises(NoAutenticado):
            _login(h, "mala1234")
    reloj.avanzar(minutes=16)
    with pytest.raises(NoAutenticado):
        _login(h, "mala1234")  # empieza una racha nueva
    assert repo.intentos["ana@unas.edu.pe"].conteo_fallidos == 1


def test_ventana_movil_de_15_minutos():
    """RF-AUT-19 / RN-39: fallos en los min 0, 10, 14, 16, 17 y 18 → a los 18 hay 5 en 8 min (10–18): bloqueo."""
    h, repo, reloj = _escenario()
    inicio = reloj.ahora()
    for minuto in (0, 10, 14, 16, 17):
        reloj.avanzar(minutes=minuto - (reloj.ahora() - inicio).total_seconds() / 60)
        with pytest.raises(NoAutenticado):
            _login(h, "mala1234")
    assert repo.intentos["ana@unas.edu.pe"].conteo_fallidos == 4  # el del min 0 salió de la ventana
    reloj.avanzar(minutes=1)  # min 18
    with pytest.raises(NoAutenticado):
        _login(h, "mala1234")
    intento = repo.intentos["ana@unas.edu.pe"]
    assert intento.conteo_fallidos == 5 and intento.bloqueado_hasta == reloj.ahora() + timedelta(minutes=15)
    with pytest.raises(DemasiadosIntentos, match="en 15 min"):
        _login(h)  # aun con la contraseña correcta


def test_intento_antiguo_sin_failed_at_se_reconstruye():
    from app.shared.db.mapeo import doc_a_intento, intento_a_doc

    t0 = FakeClock().ahora()
    doc = {"email": "a@unas.edu.pe", "failedCount": 3, "firstFailedAt": t0,
           "lastFailedAt": t0 + timedelta(minutes=2), "lockedUntil": None}
    intento = doc_a_intento(doc)
    assert intento.fallos == [t0, t0 + timedelta(minutes=2), t0 + timedelta(minutes=2)]
    assert intento_a_doc(intento)["failedAt"] == intento.fallos


def test_exito_reinicia_contador():
    h, repo, _ = _escenario()
    with pytest.raises(NoAutenticado):
        _login(h, "mala1234")
    _login(h)
    assert not repo.intentos


def test_endpoint_escribe_cookie_segura():
    from app.main import app

    h, *_ = _escenario()
    app.dependency_overrides[endpoint.get_handler] = lambda: h
    try:
        respuesta = TestClient(app).post("/api/sesiones", json={"correo": "ana@unas.edu.pe",
                                                                "contrasena": "clave123"})
    finally:
        app.dependency_overrides.clear()
    assert respuesta.status_code == 200 and respuesta.json() == {"nickname": "ana_07"}
    cookie = respuesta.headers["set-cookie"]
    assert "la_banca_sesion=" in cookie and "HttpOnly" in cookie and "Secure" in cookie
    assert "samesite=lax" in cookie.lower()  # RNF-SEG-06
