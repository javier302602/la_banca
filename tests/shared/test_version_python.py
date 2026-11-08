"""La versión de Python fijada para Vercel está soportada y coincide con la del entorno de pruebas."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SOPORTADAS_POR_VERCEL = {"3.12", "3.13", "3.14"}  # docs Vercel «Python version» (3.12 por defecto)


def test_python_version_fijada_y_soportada():
    fijada = (RAIZ / ".python-version").read_text(encoding="utf-8").strip()
    assert fijada == "3.14"
    assert fijada in SOPORTADAS_POR_VERCEL
    assert f"{sys.version_info.major}.{sys.version_info.minor}" == fijada


def test_sin_otras_fuentes_de_version_que_la_contradigan():
    # Vercel también lee pyproject.toml y Pipfile.lock y no documenta cuál prevalece
    assert not (RAIZ / "pyproject.toml").exists() and not (RAIZ / "Pipfile.lock").exists()
