"""scripts/respaldo_mongodb.py — respaldo con mongodump y rotación de 7 días (PA-37, RNF-PRI-02)."""
import importlib.util
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[2] / "scripts" / "respaldo_mongodb.py"
_spec = importlib.util.spec_from_file_location("respaldo_mongodb", RUTA)
respaldo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(respaldo)

AHORA = datetime(2026, 11, 8, 3, 0, tzinfo=timezone.utc)
URI = "mongodb+srv://usuario:cl'ave@cluster.example/?retryWrites=true"


class MongodumpFalso:
    """Simula mongodump: lee la URI del --config y escribe el archivo de --archive."""

    def __init__(self, codigo=0):
        self.codigo, self.llamadas, self.configs = codigo, [], []

    def __call__(self, comando, **opciones):
        self.llamadas.append(comando)
        config = Path(next(a for a in comando if a.startswith("--config=")).split("=", 1)[1])
        self.configs.append(config.read_text(encoding="utf-8"))
        if self.codigo == 0:
            Path(next(a for a in comando if a.startswith("--archive=")).split("=", 1)[1]).write_bytes(b"dump")
        return subprocess.CompletedProcess(comando, self.codigo, "", f"fallo de conexión a {URI}")


def _respaldo_previo(destino: Path, dias: float, base="la_banca_db") -> Path:
    archivo = destino / respaldo.nombre_archivo(base, AHORA - timedelta(days=dias))
    archivo.write_bytes(b"x")
    return archivo


def test_crea_archivo_comprimido_sin_exponer_la_uri(tmp_path, monkeypatch):
    monkeypatch.setenv("MONGO_URI", URI)
    monkeypatch.setenv("MONGO_DB", "la_banca_db")
    falso = MongodumpFalso()
    assert respaldo.main(["--destino", str(tmp_path)], ejecutar=falso, ahora=AHORA) == 0
    [comando] = falso.llamadas
    archivo = tmp_path / "la_banca_db-20261108T030000Z.archive.gz"
    assert comando[0] == "mongodump" and "--gzip" in comando and f"--archive={archivo}" in comando
    assert "--db=la_banca_db" in comando and not any(URI in a for a in comando)  # la URI no va en la línea
    assert falso.configs == ["uri: 'mongodb+srv://usuario:cl''ave@cluster.example/?retryWrites=true'\n"]
    config = Path(next(a for a in comando if a.startswith("--config=")).split("=", 1)[1])
    assert not config.exists()  # el archivo con credenciales se borra
    assert archivo.read_bytes() == b"dump"


def test_rota_respaldos_de_mas_de_7_dias(tmp_path):
    viejo = _respaldo_previo(tmp_path, 7.01)
    limite = _respaldo_previo(tmp_path, 7)
    reciente = _respaldo_previo(tmp_path, 1)
    otra_base = _respaldo_previo(tmp_path, 30, base="otra_db")
    ajeno = tmp_path / "notas.txt"
    ajeno.write_text("no tocar")
    archivo, eliminados = respaldo.respaldar(URI, "la_banca_db", tmp_path, AHORA, 7, MongodumpFalso())
    assert eliminados == [viejo] and not viejo.exists()
    assert limite.exists() and reciente.exists() and otra_base.exists() and ajeno.exists() and archivo.exists()


def test_fallo_no_rota_ni_deja_archivo_y_oculta_la_uri(tmp_path, monkeypatch, capsys):
    viejo = _respaldo_previo(tmp_path, 10)
    monkeypatch.setenv("MONGO_URI", URI)
    assert respaldo.main(["--destino", str(tmp_path)], ejecutar=MongodumpFalso(codigo=1), ahora=AHORA) == 1
    error = capsys.readouterr().err
    assert "código 1" in error and URI not in error and "<MONGO_URI>" in error
    assert viejo.exists()  # sin respaldo nuevo no se borran los anteriores
    assert sorted(p.name for p in tmp_path.iterdir()) == [viejo.name]


@pytest.mark.parametrize("dias", [0, 8, 30])
def test_retencion_fuera_de_rango_se_rechaza(tmp_path, dias):
    with pytest.raises(respaldo.ErrorRespaldo, match="RNF-PRI-02"):
        respaldo.respaldar(URI, "la_banca_db", tmp_path, AHORA, dias, MongodumpFalso())


def test_sin_uri_falla(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("MONGO_URI", raising=False)
    assert respaldo.main(["--destino", str(tmp_path)], ejecutar=MongodumpFalso(), ahora=AHORA) == 1
    assert "Falta MONGO_URI" in capsys.readouterr().err
