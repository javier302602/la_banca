"""Fase 5 — Administradores por .env, filtro de palabras, cuentas bloqueadas y acciones de moderación."""
import asyncio
import json
from datetime import timedelta

import pytest

from app.features.m01_acceso.cu02_iniciar_sesion.handler import IniciarSesionHandler
from app.features.m01_acceso.cu02_iniciar_sesion.request import IniciarSesionRequest
from app.features.m09_admin.cu26_moderar_reporte.handler import ModerarReporteHandler
from app.features.m09_admin.cu26_moderar_reporte.request import AccionRequest
from app.shared.config import moderacion
from app.shared.domain.contracts import IAdminRepository
from app.shared.domain.entities import AccionAdmin, EstadoReporte, ReporteAdmin
from app.shared.domain.errors import ErrorValidacion, NoAutenticado, Prohibido
from app.shared.security.session import ValidadorSesion
from tests.fakes import (FakeAccountRepository, FakeClock, FakeConfig, FakeEmailSender, FakeImageStorage,
                         FakePasswordHasher, SecureTokenService, estudiante)


def correr(c):
    return asyncio.run(c)


# --- Administradores (ADMIN_EMAILS) y filtro de palabras ------------------------------------------------
def test_admins_desde_env(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", " Ana@UNAS.edu.pe , beto@unas.edu.pe,, ")
    assert moderacion.correos_admin() == {"ana@unas.edu.pe", "beto@unas.edu.pe"}
    assert moderacion.es_admin("ANA@unas.edu.pe") and not moderacion.es_admin("caro@unas.edu.pe")
    monkeypatch.delenv("ADMIN_EMAILS")
    assert not moderacion.es_admin("ana@unas.edu.pe")


@pytest.fixture
def palabras(tmp_path, monkeypatch):
    archivo = tmp_path / "palabras.json"
    archivo.write_text(json.dumps({"palabras": ["tonto", "Estúpido", "mala palabra"]}), encoding="utf-8")
    monkeypatch.setenv("PALABRAS_OFENSIVAS_ARCHIVO", str(archivo))
    moderacion._patrones.cache_clear()
    yield
    moderacion._patrones.cache_clear()


def test_filtro_sin_tildes_ni_mayusculas_y_palabra_completa(palabras):
    assert moderacion.palabras_ofensivas("Eres un TONTO y un estupido") == ["tonto", "estupido"]
    assert moderacion.palabras_ofensivas("Qué tontería") == []        # no marca partes de otra palabra
    assert moderacion.palabras_ofensivas("dijo una mala   palabra") == []  # la frase exacta, con un espacio
    assert moderacion.palabras_ofensivas("dijo una mala palabra") == ["mala palabra"]
    assert moderacion.palabras_ofensivas(None) == []


def test_la_lista_del_repositorio_es_valida():
    moderacion._patrones.cache_clear()
    assert moderacion.palabras_ofensivas("eres un idiota") == ["idiota"]


# --- Cuentas suspendidas o baneadas ------------------------------------------------------------------------
def _sesion(**cuenta):
    repo, reloj = FakeAccountRepository(), FakeClock()
    token, token_hash = SecureTokenService().generar()
    e = estudiante(**cuenta)
    eid = correr(repo.crear(e))
    from app.shared.domain.entities import Sesion
    correr(repo.crear_sesion(Sesion("", eid, token_hash, reloj.ahora(), reloj.ahora(), reloj.ahora() + timedelta(hours=1))))
    return ValidadorSesion(repo, FakeConfig(), reloj), token, repo, reloj


def test_sesion_de_cuenta_suspendida_o_baneada_se_cierra():
    ahora = FakeClock().ahora()
    for cuenta, mensaje in (({"suspendido_hasta": ahora + timedelta(days=3)}, "suspendida hasta"),
                            ({"baneado": True}, "bloqueada")):
        validador, token, repo, _ = _sesion(**cuenta)
        with pytest.raises(NoAutenticado, match=mensaje) as error:
            correr(validador.validar(token))
        assert error.value.codigo == "cuenta_bloqueada"
        assert all(s.estado.value == "CLOSED" for s in repo.sesiones.values())


def test_suspension_vencida_vuelve_a_permitir_entrar():
    validador, token, _, reloj = _sesion(suspendido_hasta=FakeClock().ahora() + timedelta(minutes=5))
    reloj.avanzar(minutes=5)
    assert correr(validador.validar(token)).nickname == "ana_07"


def test_sesion_indica_admin_y_aviso(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "ana@unas.edu.pe")
    validador, token, *_ = _sesion(aviso_pendiente="Cuida tu lenguaje")
    sesion = correr(validador.validar(token))
    assert sesion.es_admin and sesion.aviso == "Cuida tu lenguaje"


def test_login_rechaza_cuenta_baneada():
    repo = FakeAccountRepository()
    correr(repo.crear(estudiante(password_hash=FakePasswordHasher().hash("clave123"), baneado=True)))
    h = IniciarSesionHandler(repo, FakePasswordHasher(), SecureTokenService(), FakeConfig(), FakeClock())
    with pytest.raises(Prohibido, match="bloqueada"):
        correr(h.handle(IniciarSesionRequest(correo="ana@unas.edu.pe", contrasena="clave123")))


# --- Acciones de moderación (CU-26) ------------------------------------------------------------------------
class FakeAdmin(IAdminRepository):
    def __init__(self, reporte, cuentas):
        self.reporte, self.cuentas = reporte, cuentas
        self.hecho, self.historial_acciones = [], []

    async def buscar_reporte(self, origen, reporte_id):
        return self.reporte if reporte_id == self.reporte.id else None

    async def marcar_reporte(self, origen, reporte_id, estado, accion):
        self.reporte.estado = estado
        self.reporte.acciones.append(accion)

    async def buscar_cuenta(self, estudiante_id):
        return self.cuentas.get(estudiante_id)

    async def eliminar_publicacion(self, publicacion_id, ahora):
        self.hecho.append(("ocultar", publicacion_id))

    async def eliminar_chat(self, chat_id):
        self.hecho.append(("borrar_chat", chat_id))
        return ["documentos/x.pdf"]

    async def advertir(self, estudiante_id, texto):
        self.hecho.append(("advertir", estudiante_id, texto))

    async def suspender(self, estudiante_id, hasta, ahora):
        self.hecho.append(("suspender", estudiante_id, hasta - ahora))

    async def banear(self, estudiante_id, ahora):
        self.hecho.append(("banear", estudiante_id))

    async def registrar_accion(self, accion):
        self.historial_acciones.append(accion)


def _moderar(tipo="PUBLICACION", reportado="u_malo", admins=""):
    reporte = ReporteAdmin("contenido", "r1", tipo, "INAPPROPRIATE", "", FakeClock().ahora(), EstadoReporte.PENDIENTE,
                           False, "u_bueno", reportado, "obj1")
    cuentas = {"u_malo": estudiante(correo="malo@unas.edu.pe", nickname="malo"),
               "u_admin": estudiante(correo="jefa@unas.edu.pe", nickname="jefa")}
    cuentas["u_malo"].id, cuentas["u_admin"].id = "u_malo", "u_admin"
    repo, correo = FakeAdmin(reporte, cuentas), FakeEmailSender()
    return ModerarReporteHandler(repo, FakeImageStorage(), correo, FakeClock()), repo, correo


def test_eliminar_publicacion_y_chat():
    h, repo, _ = _moderar()
    r = correr(h.handle("u_admin", "contenido", "r1", AccionRequest(accion="ELIMINAR_CONTENIDO")))
    assert repo.hecho == [("ocultar", "obj1")] and r.estado is EstadoReporte.RESUELTO
    h, repo, _ = _moderar(tipo="CHAT")
    correr(h.handle("u_admin", "contenido", "r1", AccionRequest(accion="ELIMINAR_CONTENIDO")))
    assert repo.hecho == [("borrar_chat", "obj1")]


def test_videollamada_no_tiene_contenido_que_borrar():
    h, *_ = _moderar(tipo="VIDEOLLAMADA")
    with pytest.raises(ErrorValidacion, match="no guarda contenido"):
        correr(h.handle("u_admin", "videollamada", "r1", AccionRequest(accion="ELIMINAR_CONTENIDO")))


def test_advertir_suspender_y_banear_avisan_por_correo_y_quedan_en_el_historial():
    h, repo, correo = _moderar()
    correr(h.handle("u_admin", "contenido", "r1", AccionRequest(accion="ADVERTIR", mensaje="  Sin insultos ")))
    correr(h.handle("u_admin", "contenido", "r1", AccionRequest(accion="SUSPENDER", dias=3)))
    correr(h.handle("u_admin", "contenido", "r1", AccionRequest(accion="BANEAR")))
    assert repo.hecho == [("advertir", "u_malo", "Sin insultos"), ("suspender", "u_malo", timedelta(days=3)),
                          ("banear", "u_malo")]
    assert [c.destinatario for c in correo.enviados] == ["malo@unas.edu.pe"] * 3
    assert [a["action"] for a in repo.historial_acciones] == ["ADVERTIR", "SUSPENDER", "BANEAR"]
    assert all(a["adminId"] == "u_admin" and a["userId"] == "u_malo" for a in repo.historial_acciones)


def test_descartar_no_toca_la_cuenta():
    h, repo, correo = _moderar()
    r = correr(h.handle("u_admin", "contenido", "r1", AccionRequest(accion="DESCARTAR")))
    assert r.estado is EstadoReporte.DESCARTADO and repo.hecho == [] and correo.enviados == []


def test_no_se_sanciona_a_un_administrador(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "jefa@unas.edu.pe")
    h, *_ = _moderar(reportado="u_admin")
    with pytest.raises(Prohibido, match="administrador"):
        correr(h.handle("u_otro_admin", "contenido", "r1", AccionRequest(accion="BANEAR")))


def test_suspender_exige_dias():
    with pytest.raises(ValueError, match="cuántos días"):
        AccionRequest(accion=AccionAdmin.SUSPENDER)
    with pytest.raises(ValueError):
        AccionRequest(accion="SUSPENDER", dias=400)
