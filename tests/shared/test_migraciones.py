"""Migraciones versionadas (SRS v2.0, Fase 6): descubrimiento, orden y formato. Contra Mongo: tests/e2e."""
from pathlib import Path

import pytest

from app.shared.db import migraciones


def test_descubre_las_del_proyecto_en_orden():
    nombres = [n for n, _ in migraciones.descubrir()]
    assert nombres[0] == "001_v1_a_v2" and nombres == sorted(nombres)
    modulo = migraciones.cargar(*migraciones.descubrir()[0])
    assert modulo.DESCRIPCION and callable(modulo.aplicar)


def test_ignora_archivos_que_no_siguen_el_patron_y_rechaza_numeros_repetidos(tmp_path: Path):
    (tmp_path / "002_b.py").write_text("async def aplicar(db): return {}", encoding="utf-8")
    (tmp_path / "001_a.py").write_text("async def aplicar(db): return {}", encoding="utf-8")
    (tmp_path / "notas.py").write_text("", encoding="utf-8")
    (tmp_path / "3_mal.py").write_text("", encoding="utf-8")
    assert [n for n, _ in migraciones.descubrir(tmp_path)] == ["001_a", "002_b"]
    (tmp_path / "002_c.py").write_text("async def aplicar(db): return {}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="mismo número"):
        migraciones.descubrir(tmp_path)


def test_una_migracion_sin_aplicar_no_se_carga(tmp_path: Path):
    (tmp_path / "001_x.py").write_text("DESCRIPCION = 'x'", encoding="utf-8")
    with pytest.raises(RuntimeError, match="aplicar"):
        migraciones.cargar("001_x", tmp_path / "001_x.py")


def test_sin_mongo_uri_el_arranque_no_migra(monkeypatch):
    import asyncio

    monkeypatch.delenv("MONGO_URI", raising=False)
    assert asyncio.run(migraciones.aplicar_al_arrancar()) == []


def test_scripts_de_respaldo_y_restauracion():
    raiz = Path(__file__).resolve().parents[2]
    backup = (raiz / "scripts/backup.sh").read_text(encoding="utf-8")
    restore = (raiz / "scripts/restore.sh").read_text(encoding="utf-8")
    assert "mongodump" in backup and "--archive --gzip" in backup and "mc mirror" in backup
    assert "MANIFIESTO.txt" in backup and "tar -czf" in backup and '"$DIAS" -gt 7' in backup
    assert "mongorestore" in restore and "--drop" in restore and "--nsFrom" in restore
    assert "db.dropDatabase()" in restore  # un respaldo de v1 no hereda el registro de migraciones actual
    assert "*.archive.gz)" in restore  # acepta respaldos de la v1
    assert "scripts.migrar" in restore
