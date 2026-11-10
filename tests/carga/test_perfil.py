"""El perfil de carga corresponde al criterio de RNF-REN-01 y la evaluación aplica los límites del SRS."""
from pathlib import Path

from tests.carga import perfil


def test_perfil_de_rnf_ren_01():
    pesos = {clase: peso for clase, (peso, _) in perfil.PERFIL.items()}
    assert sum(pesos.values()) == 10
    assert {c: p / 10 for c, p in pesos.items()} == {"LectorFeed": 0.6, "Conversador": 0.3, "Publicador": 0.1}
    assert {c: s for c, (_, s) in perfil.PERFIL.items()} == {"LectorFeed": 30, "Conversador": 20, "Publicador": 120}
    assert (perfil.USUARIOS, perfil.DURACION) == (100, "15m")
    assert (perfil.CUENTAS_REGISTRADAS, perfil.PUBLICACIONES_ACTIVAS) == (10_000, 3_000)


def test_locustfile_usa_el_perfil():
    texto = (Path(__file__).with_name("locustfile.py")).read_text(encoding="utf-8")
    for clase in perfil.PERFIL:
        assert f"class {clase}(HttpUser)" in texto and f'perfil.PERFIL["{clase}"]' in texto
    assert "constant_pacing" in texto and "X-Actualizacion-Automatica" in texto


def test_transferencia_a_10_mbps():
    assert perfil.segundos_de_transferencia(5 * 1024 * 1024) == 5 * 1024 * 1024 * 8 / 10_000_000


def _p95(feed=1000, filtro=1200, texto=1500, imagen=8000, correo=400):
    return {perfil.FEED: feed, perfil.FEED_FILTRO: filtro, perfil.ENTREGA_TEXTO: texto, perfil.ENTREGA_IMAGEN: imagen,
            perfil.CORREO: correo}


def test_evaluar_dentro_de_los_limites():
    resultados = perfil.evaluar(10_000, 9, _p95(), 10_000, 3_000)
    assert [r.rnf for r in resultados] == ["RNF-REN-01", "RNF-REN-02", "RNF-REN-03", "RNF-REN-04", "RNF-REN-05",
                                           "RNF-REN-06"]
    assert all(r.cumple for r in resultados)
    assert resultados[1].valor == 1.2  # el peor de los dos p95 del feed


def test_evaluar_fuera_de_los_limites():
    malos = {r.rnf: r.cumple for r in perfil.evaluar(1_000, 10, _p95(filtro=3100, texto=2001, imagen=10_001,
                                                                     correo=30_001), 10_000, 2_999)}
    assert not any(malos.values())  # 1 % de errores no es < 1 %; 2 999 activas no alcanzan PA-35
