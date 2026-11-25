"""Fase 4 — Carreras del perfil leídas de config/carreras.json (editable, sin carreras en el código)."""
import json

import pytest
from pydantic import ValidationError

from app.features.m07_perfiles.cu19_editar_perfil.request import EditarIdentidadRequest
from app.shared.config import carreras as modulo


@pytest.fixture
def lista(tmp_path, monkeypatch):
    """Usa un archivo temporal como lista de carreras y limpia la caché antes y después."""
    archivo = tmp_path / "carreras.json"

    def escribir(contenido):
        archivo.write_text(json.dumps(contenido), encoding="utf-8")
        modulo.carreras.cache_clear()

    monkeypatch.setenv("CARRERAS_ARCHIVO", str(archivo))
    yield escribir
    modulo.carreras.cache_clear()


def test_el_archivo_del_repositorio_es_valido():
    modulo.carreras.cache_clear()
    assert len(modulo.carreras()) >= 1


def test_lee_normaliza_y_quita_repetidas(lista):
    lista({"carreras": ["Agronomía", "  Zootecnia ", "Agronomía"]})
    assert modulo.carreras() == ("Agronomía", "Zootecnia")


@pytest.mark.parametrize("contenido", [{"carreras": []}, {"carreras": ["", "x"]}, ["Agronomía"], {"otra": 1}])
def test_archivo_mal_formado_da_un_error_claro(lista, contenido):
    lista(contenido)
    with pytest.raises(RuntimeError, match="carreras"):
        modulo.carreras()


def test_solo_se_acepta_una_carrera_de_la_lista(lista):
    lista({"carreras": ["Agronomía", "Zootecnia"]})
    assert EditarIdentidadRequest(nombre="Ana Ríos", carrera="Zootecnia").carrera == "Zootecnia"
    with pytest.raises(ValidationError, match="Elige una carrera de la lista"):
        EditarIdentidadRequest(nombre="Ana Ríos", carrera="Medicina")
