""".github/workflows/backup.yml — respaldo diario cifrado, retención de 7 días, inactivo sin el secret."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "backup.yml"
TEXTO = RUTA.read_text(encoding="utf-8")


def _bash() -> str | None:
    """En Windows, el bash de Git for Windows (System32/bash.exe es el de WSL, que puede no estar instalado)."""
    if sys.platform == "win32" and shutil.which("git"):
        for carpeta in Path(shutil.which("git")).resolve().parents:
            if (carpeta / "bin" / "bash.exe").exists():
                return str(carpeta / "bin" / "bash.exe")
        return None
    return shutil.which("bash")


BASH = _bash()


def _pasos() -> str:
    return TEXTO.split("steps:", 1)[1]


def test_programado_a_diario_y_manual():
    assert 'cron: "0 8 * * *"' in TEXTO and "workflow_dispatch:" in TEXTO
    assert "permissions:\n  contents: read" in TEXTO


def test_ejecuta_el_script_versionado_y_sube_artifact_de_7_dias():
    assert "python scripts/respaldo_mongodb.py --destino respaldos" in TEXTO
    assert "actions/upload-artifact@v4" in TEXTO and "retention-days: 7" in TEXTO
    assert "if-no-files-found: error" in TEXTO


def test_sube_solo_el_volcado_cifrado():
    assert "path: respaldos/*.archive.gz.gpg" in TEXTO
    assert "--symmetric --cipher-algo AES256" in TEXTO and 'rm "$archivo"' in TEXTO
    # la frase va por la entrada estándar, no en la línea de comandos
    assert '--passphrase-fd 0' in TEXTO and '<<< "$BACKUP_PASSPHRASE"' in TEXTO


def test_se_activa_solo_con_el_secret_y_exige_cifrado():
    assert "MONGO_URI: ${{ secrets.MONGO_URI }}" in TEXTO
    assert "BACKUP_PASSPHRASE: ${{ secrets.BACKUP_PASSPHRASE }}" in TEXTO
    pasos = _pasos()
    # todos los pasos posteriores a la comprobación dependen de que exista MONGO_URI
    assert pasos.count("if: steps.secretos.outputs.activo == 'true'") == 6
    assert "${{ secrets" not in pasos  # los secrets llegan por env, no interpolados en los scripts


@pytest.mark.skipif(BASH is None, reason="bash no disponible")
@pytest.mark.parametrize("uri,frase,codigo,activo", [
    ("", "", 0, None), ("", "x", 0, None),           # sin MONGO_URI: termina sin error y no se activa
    ("mongodb://h", "", 1, None),                     # con MONGO_URI pero sin frase: falla
    ("mongodb://h", "frase", 0, "activo=true"),
])
def test_paso_de_comprobacion(tmp_path, uri, frase, codigo, activo):
    script = _pasos().split("run: |", 1)[1].split("\n      - ", 1)[0]
    script = "\n".join(linea[10:] for linea in script.splitlines())
    salida = tmp_path / "salida"
    salida.touch()
    r = subprocess.run([BASH, "-c", script], capture_output=True, text=True,
                       env={**os.environ, "MONGO_URI": uri, "BACKUP_PASSPHRASE": frase, "GITHUB_OUTPUT": str(salida)})
    assert r.returncode == codigo, r.stdout + r.stderr
    contenido = salida.read_text()
    assert (activo in contenido) if activo else ("activo=true" not in contenido)
