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


def test_workflow_de_github_cada_hora_en_un_solo_job():
    from pathlib import Path

    texto = (Path(__file__).resolve().parents[3] / ".github" / "workflows" / "jobs.yml").read_text(encoding="utf-8")
    assert 'cron: "0 * * * *"' in texto
    assert "matrix" not in texto and texto.count("runs-on:") == 1  # un solo job: ~1 minuto por ejecución
    assert "timeout-minutes: 2" in texto
    posiciones = [texto.index(f"/jobs/{job}") for job in ("ea03-limpiar-chats-expirados",
                                                           "ea05-depurar-contenido-reportado",
                                                           "ea07-eliminar-cuentas-no-activadas")]
    assert posiciones == sorted(posiciones)  # pasos secuenciales en orden
    assert texto.count("if: ${{ !cancelled() }}") == 3
    assert "secrets.CRON_SECRET" in texto and "secrets.APP_BASE_URL" in texto
    assert texto.count('Authorization: Bearer ${CRON_SECRET}') == 3
    assert "${{ secrets" not in texto.split("steps:")[1]  # los secrets llegan por env, no interpolados en scripts


def test_repositorio_consulta_por_ix_accounts_activation_exp():
    """EA-07 usa el índice del Entregable 2 con un límite que no deja fuera ninguna cuenta vencida."""
    from datetime import datetime, timezone

    from app.jobs.ea07_eliminar_cuentas_no_activadas.repository import MongoEliminarCuentasRepository

    class Coleccion:
        def __init__(self):
            self.llamadas = []

        async def delete_many(self, filtro, **opciones):
            self.llamadas.append((filtro, opciones))
            return type("Resultado", (), {"deleted_count": 2})()

    coleccion = Coleccion()
    db = type("Db", (), {"accounts": coleccion})()
    corte = datetime(2026, 10, 2, 14, 0, tzinfo=timezone.utc)
    assert asyncio.run(MongoEliminarCuentasRepository(db).eliminar_no_activadas(corte)) == 2
    filtro, opciones = coleccion.llamadas[0]
    assert opciones == {"hint": "ix_accounts_activation_exp"}
    # último enlace posible: emitido justo antes de las 72 h y vigente 24 h más → corte + 96 h
    assert filtro["activation.expiresAt"] == {"$lte": corte + timedelta(hours=96)}
    assert filtro["status"] == "PENDIENTE_ACTIVACION" and filtro["createdAt"] == {"$lte": corte}
