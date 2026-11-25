"""CU-23 / CU-24 — Videollamada aleatoria: emparejamiento, señales, chat, siguiente, colgar y reporte."""
import asyncio

import pytest

from app.features.m08_videollamada.cu23_videollamada.handler import VideollamadaHandler
from app.features.m08_videollamada.cu24_reportar_videollamada.handler import ReportarVideollamadaHandler
from app.features.m08_videollamada.cu24_reportar_videollamada.request import ReportarVideollamadaRequest
from app.shared.domain.entities import MotivoReporteVideollamada, ParticipanteVideollamada
from app.shared.domain.errors import NoEncontrado
from tests.fakes import FakeClock, FakeVideollamadaRepository

ANA = ParticipanteVideollamada("ana", "ana_07", "Ana Ríos", "Ingeniería en Informática y Sistemas")
BETO = ParticipanteVideollamada("beto", "beto_9", "Beto Paz", "Agronomía")
CARO = ParticipanteVideollamada("caro", "caro_3", "Caro Luna", "Zootecnia")
SIN_PERFIL = ParticipanteVideollamada("dani", "dani_1", "", "")


def correr(c):
    return asyncio.run(c)


@pytest.fixture
def mundo():
    repo = FakeVideollamadaRepository([ANA, BETO, CARO, SIN_PERFIL])
    reloj = FakeClock()
    h = VideollamadaHandler(repo, reloj)
    return h, repo, reloj


def _conectar(h, *ids):
    return [correr(h.conectar(i)) for i in ids]


def _emparejar(h, a, b):
    """a y b buscan; a intenta emparejar y toma a b; b se entera por su buzón."""
    correr(h.buscar(a))
    correr(h.buscar(b))
    respuesta_a = correr(h.intentar_emparejar(a))
    respuesta_b = correr(h.leer_buzon(b))
    return respuesta_a, respuesta_b


def test_sin_nombre_y_carrera_no_entra(mundo):
    h, *_ = mundo
    assert correr(h.conectar("dani")) is None
    assert correr(h.conectar("nadie")) is None


def test_empareja_a_dos_estudiantes_y_se_ven_nombre_y_carrera(mundo):
    h, repo, _ = mundo
    ana, beto = _conectar(h, "ana", "beto")
    para_ana, para_beto = _emparejar(h, ana, beto)
    assert para_ana[0]["pareja"] == {"nombre": "Beto Paz", "carrera": "Agronomía", "nickname": "beto_9"}
    assert para_ana[0]["iniciador"] is True and para_beto[0]["iniciador"] is False
    assert para_beto[0]["pareja"]["nombre"] == "Ana Ríos" and "pareja_id" not in para_beto[0]
    assert ana.sala_id == beto.sala_id and ana.estado == beto.estado == "en_llamada"
    assert repo.salas[ana.sala_id].participantes == ["ana", "beto"] and not repo.cola


def test_solo_no_empareja_y_renueva_su_lugar(mundo):
    h, repo, _ = mundo
    (ana,) = _conectar(h, "ana")
    assert correr(h.buscar(ana)) == [{"tipo": "esperando"}]
    assert correr(h.intentar_emparejar(ana)) == []
    assert "ana" in repo.cola and ana.estado == "esperando"


def test_senales_y_chat_llegan_solo_a_la_pareja(mundo):
    h, repo, _ = mundo
    ana, beto = _conectar(h, "ana", "beto")
    _emparejar(h, ana, beto)
    correr(h.reenviar(ana, {"tipo": "senal", "datos": {"descripcion": {"type": "offer", "sdp": "v=0"}}}))
    correr(h.reenviar(ana, {"tipo": "chat", "texto": "  hola   Beto "}))
    recibido = correr(h.leer_buzon(beto))
    assert [m["tipo"] for m in recibido] == ["senal", "chat"]
    assert recibido[1]["texto"] == "hola   Beto" and recibido[0]["datos"]["descripcion"]["type"] == "offer"
    assert correr(h.reenviar(ana, {"tipo": "chat", "texto": "x" * 501}))[0]["tipo"] == "error"
    assert correr(h.reenviar(ana, {"tipo": "senal", "datos": "no es un objeto"}))[0]["tipo"] == "error"


def test_colgar_avisa_y_cierra_la_sala(mundo):
    h, repo, _ = mundo
    ana, beto = _conectar(h, "ana", "beto")
    _emparejar(h, ana, beto)
    sala = ana.sala_id
    assert correr(h.colgar(ana)) == [{"tipo": "colgado"}]
    assert correr(h.leer_buzon(beto)) == [{"tipo": "colgo", "sala": sala}]
    assert beto.estado == "inactivo" and repo.salas[sala].fin is not None


def test_siguiente_no_repite_a_la_misma_persona(mundo):
    h, repo, _ = mundo
    ana, beto, caro = _conectar(h, "ana", "beto", "caro")
    _emparejar(h, ana, beto)
    correr(h.siguiente(ana))                  # Ana evita a Beto
    correr(h.leer_buzon(beto))                # Beto recibe «colgo»
    correr(h.buscar(beto))
    assert correr(h.intentar_emparejar(ana)) == []  # solo está Beto en la cola: no se repite
    correr(h.buscar(caro))
    assert correr(h.intentar_emparejar(ana))[0]["pareja"]["nickname"] == "caro_3"


def test_emparejado_tardio_tras_colgar_se_devuelve(mundo):
    """Si me tomaron justo cuando colgué, le aviso a quien me tomó para que no quede esperando."""
    h, repo, _ = mundo
    ana, beto = _conectar(h, "ana", "beto")
    correr(h.buscar(ana))
    correr(h.buscar(beto))
    correr(h.intentar_emparejar(ana))         # Ana toma a Beto
    correr(h.colgar(beto))                    # Beto colgó antes de leer el aviso
    correr(h.colgar(ana))                     # (Ana también cuelga para leer limpio)
    repo.buzones.pop("beto", None)
    correr(h.buscar(ana))
    correr(h.buscar(beto))
    correr(h.intentar_emparejar(beto))        # ahora Beto toma a Ana…
    ana.estado = "inactivo"                   # …pero Ana ya no está esperando
    assert correr(h.leer_buzon(ana)) == []
    assert repo.buzones["beto"][0]["tipo"] == "colgo"


def test_mensajes_de_otra_sala_se_ignoran(mundo):
    h, repo, _ = mundo
    ana, beto = _conectar(h, "ana", "beto")
    _emparejar(h, ana, beto)
    correr(repo.enviar("beto", {"tipo": "chat", "sala": "sala-vieja", "texto": "viejo"}, None))
    assert correr(h.leer_buzon(beto)) == []


# --- CU-24 Reportar --------------------------------------------------------------------------------------
def test_reporta_a_la_otra_persona_de_la_sala(mundo):
    h, repo, reloj = mundo
    ana, beto = _conectar(h, "ana", "beto")
    _emparejar(h, ana, beto)
    reportar = ReportarVideollamadaHandler(repo, reloj)
    r = correr(reportar.handle("beto", ReportarVideollamadaRequest(sala_id=ana.sala_id, motivo="INSULTOS",
                                                                   detalle="  me   insultó ")))
    assert r.id and "Reporte enviado" in r.mensaje
    reporte = repo.reportes[0]
    assert (reporte.reportante_id, reporte.reportado_id) == ("beto", "ana")
    assert reporte.motivo is MotivoReporteVideollamada.INSULTOS and reporte.detalle == "me insultó"


def test_no_se_reporta_una_sala_ajena_o_inexistente(mundo):
    h, repo, reloj = mundo
    ana, beto = _conectar(h, "ana", "beto")
    _emparejar(h, ana, beto)
    reportar = ReportarVideollamadaHandler(repo, reloj)
    for quien, sala in (("caro", ana.sala_id), ("ana", "no-existe")):
        with pytest.raises(NoEncontrado):
            correr(reportar.handle(quien, ReportarVideollamadaRequest(sala_id=sala, motivo="SPAM")))
    with pytest.raises(ValueError):
        ReportarVideollamadaRequest(sala_id=ana.sala_id, motivo="NO_EXISTE")
