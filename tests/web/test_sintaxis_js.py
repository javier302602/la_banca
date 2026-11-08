"""Todo el JS del frontend debe ser sintácticamente válido (un error deja la página entera sin funcionar)."""
import shutil
import subprocess
from pathlib import Path

import pytest

ARCHIVOS = sorted((Path(__file__).resolve().parents[2] / "web" / "static" / "js").glob("*.js"))


@pytest.mark.skipif(shutil.which("node") is None, reason="node no disponible")
@pytest.mark.parametrize("archivo", ARCHIVOS, ids=lambda p: p.name)
def test_js_sin_errores_de_sintaxis(archivo):
    resultado = subprocess.run(["node", "--check", str(archivo)], capture_output=True, text=True, timeout=30)
    assert resultado.returncode == 0, resultado.stderr
