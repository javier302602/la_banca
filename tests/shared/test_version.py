"""Versionado: VERSION (SemVer), /api/salud, pie de página y CHANGELOG (Keep a Changelog)."""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.shared import version

RAIZ = Path(__file__).resolve().parents[2]
SEMVER = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$")


def test_version_semver_y_compartida_por_la_app():
    assert SEMVER.match(version.VERSION), version.VERSION
    assert (RAIZ / "VERSION").read_text(encoding="utf-8").strip() == version.VERSION
    assert app.version == version.VERSION


class _Base:
    def __init__(self, falla=None):
        self.falla = falla

    async def command(self, nombre):
        if self.falla:
            raise self.falla
        return {"ok": 1}


@pytest.mark.parametrize("base,status,estado", [
    (_Base(), 200, "ok"),
    (None, 503, "no_disponible"),
])
def test_salud(monkeypatch, base, status, estado):
    from pymongo.errors import ServerSelectionTimeoutError

    from app.shared.db import mongo

    monkeypatch.setattr(mongo, "base_de_datos", lambda: base or _Base(ServerSelectionTimeoutError("caída")))
    r = TestClient(app).get("/api/salud")
    assert r.status_code == status
    assert r.json() == {"estado": "ok" if status == 200 else "degradado", "version": version.VERSION,
                        "base_de_datos": estado}
    assert r.headers["cache-control"] == "no-store"


def test_salud_sin_configuracion(monkeypatch):
    from app.shared.db import mongo

    def sin_uri():
        raise RuntimeError("Falta configurar MONGO_URI")

    monkeypatch.setattr(mongo, "base_de_datos", sin_uri)
    assert TestClient(app).get("/api/salud").json()["base_de_datos"] == "no_configurada"


def test_version_en_el_pie():
    from app.shared.security.session import get_sesion_opcional

    app.dependency_overrides[get_sesion_opcional] = lambda: None
    try:
        html = TestClient(app).get("/terminos").text
    finally:
        app.dependency_overrides.clear()
    assert f'<span class="ms-auto py-1" id="version-app">Versión {version.VERSION}</span>' in html


def test_changelog_keep_a_changelog():
    texto = (RAIZ / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "keepachangelog.com" in texto and "semver.org" in texto
    secciones = re.findall(r"^## \[([^\]]+)\]", texto, re.M)
    assert secciones[0] == "Unreleased" and "2.0.0" in secciones and "1.0.0" in secciones
    assert secciones.index("2.0.0") < secciones.index("1.0.0")  # más reciente primero
    for tipo in re.findall(r"^### (\w+)", texto, re.M):
        assert tipo in {"Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"}, tipo
