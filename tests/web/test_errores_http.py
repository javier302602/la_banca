"""RNF-USA-05: los 404 y 405 se responden en español (página HTML al navegar, JSON en la API)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

HTML = {"Accept": "text/html,application/xhtml+xml"}


@pytest.fixture
def cliente():
    return TestClient(app)


@pytest.mark.parametrize("ruta", ["/no-existe", "/publicaciones/abc/otra/cosa", "/chats/c1/nada"])
def test_404_de_navegacion_es_una_pagina_en_espanol(cliente, ruta):
    r = cliente.get(ruta, headers=HTML)
    assert r.status_code == 404 and r.headers["content-type"].startswith("text/html")
    assert '<html lang="es-PE">' in r.text and "Página no encontrada" in r.text and "Ir al inicio" in r.text
    assert "Not Found" not in r.text


def test_405_de_navegacion_es_una_pagina_en_espanol(cliente):
    r = cliente.put("/feed", headers=HTML)
    assert r.status_code == 405 and "Acción no permitida" in r.text and "Method Not Allowed" not in r.text
    assert "GET" in r.headers["allow"]


@pytest.mark.parametrize("metodo,ruta,status,codigo", [
    ("get", "/api/no-existe", 404, "no_encontrado"),
    ("get", "/static/js/no-existe.js", 404, "no_encontrado"),
    ("get", "/jobs/no-existe", 404, "no_encontrado"),
    ("put", "/api/feed", 405, "metodo_no_permitido"),
    ("delete", "/api/publicaciones/abc/reportes", 405, "metodo_no_permitido"),
])
def test_api_responde_json_en_espanol(cliente, metodo, ruta, status, codigo):
    r = getattr(cliente, metodo)(ruta, headers=HTML)  # aunque el navegador pida HTML, /api y /static son JSON
    assert r.status_code == status and r.headers["content-type"] == "application/json"
    datos = r.json()
    assert datos["codigo"] == codigo and datos["detail"] in (
        "La dirección que buscas no existe o ya no está disponible.", "Esta dirección no admite la acción solicitada.")
    if status == 405:
        assert r.headers["allow"]


def test_otros_errores_http_conservan_su_mensaje(cliente, monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "s3cr3t")
    r = cliente.get("/jobs/ea03-limpiar-chats-expirados")
    assert r.status_code == 401 and r.json() == {"detail": "No autorizado"}
