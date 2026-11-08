"""EA-07 — Eliminar las cuentas no activadas."""
import asyncio
from datetime import timedelta

from app.jobs.ea07_eliminar_cuentas_no_activadas.handler import EliminarCuentasNoActivadasHandler
from app.shared.domain.entities import EstadoCuenta
from tests.fakes import FakeAccountRepository, FakeClock, estudiante


def test_elimina_pendientes_con_72_horas_y_respeta_activas():
    repo, reloj = FakeAccountRepository(), FakeClock()
    inicio = reloj.ahora()
    pendiente = asyncio.run(repo.crear(estudiante(estado=EstadoCuenta.PENDIENTE_ACTIVACION, fecha=inicio)))
    activa = asyncio.run(repo.crear(estudiante(correo="b@unas.edu.pe", nickname="beto", fecha=inicio)))
    h = EliminarCuentasNoActivadasHandler(repo, reloj)
    reloj.avanzar(hours=71, minutes=59)
    assert asyncio.run(h.handle()) == {"cuentas_eliminadas": 0}
    reloj.avanzar(minutes=1)
    assert asyncio.run(h.handle()) == {"cuentas_eliminadas": 1}
    assert pendiente not in repo.cuentas and activa in repo.cuentas
    assert not asyncio.run(repo.existe_por_nickname("ana_07"))  # nickname liberado


def test_cron_exige_secreto(monkeypatch):
    from fastapi.testclient import TestClient

    from app.jobs.ea07_eliminar_cuentas_no_activadas import endpoint
    from app.main import app

    app.dependency_overrides[endpoint.get_handler] = lambda: EliminarCuentasNoActivadasHandler(
        FakeAccountRepository(), FakeClock())
    try:
        monkeypatch.setenv("CRON_SECRET", "s3cr3t")
        cliente, ruta = TestClient(app), "/jobs/ea07-eliminar-cuentas-no-activadas"
        assert cliente.get(ruta).status_code == 401
        assert cliente.get(ruta, headers={"Authorization": "Bearer s3cr3t"}).json() == {"cuentas_eliminadas": 0}
    finally:
        app.dependency_overrides.clear()


def test_vercel_json_programa_los_tres_crons():
    import json
    from pathlib import Path

    config = json.loads((Path(__file__).resolve().parents[3] / "vercel.json").read_text(encoding="utf-8"))
    rutas = {c["path"] for c in config["crons"]}
    assert rutas == {"/jobs/ea03-limpiar-chats-expirados", "/jobs/ea05-depurar-contenido-reportado",
                     "/jobs/ea07-eliminar-cuentas-no-activadas"}
    assert config["rewrites"] == [{"source": "/(.*)", "destination": "/api/index"}]
