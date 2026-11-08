"""CU-03 — Cerrar sesión manualmente."""
import asyncio
from datetime import timedelta

from app.features.m01_acceso.cu03_cerrar_sesion.handler import CerrarSesionHandler
from app.shared.domain.entities import EstadoSesion, Sesion
from tests.fakes import FakeAccountRepository, FakeClock, SecureTokenService


def test_cierra_solo_la_sesion_actual():
    repo, reloj, tokens = FakeAccountRepository(), FakeClock(), SecureTokenService()
    ahora = reloj.ahora()
    planos = []
    for _ in range(2):
        plano, hash_ = tokens.generar()
        planos.append(plano)
        asyncio.run(repo.crear_sesion(Sesion("", "u1", hash_, ahora, ahora, ahora + timedelta(hours=12))))
    asyncio.run(CerrarSesionHandler(repo, tokens, reloj).handle(planos[0]))
    estados = sorted(s.estado.value for s in repo.sesiones.values())
    assert estados == [EstadoSesion.ACTIVE.value, EstadoSesion.CLOSED.value]  # RN-38


def test_es_idempotente_sin_token_o_con_token_desconocido():
    h = CerrarSesionHandler(FakeAccountRepository(), SecureTokenService(), FakeClock())
    asyncio.run(h.handle(None))
    asyncio.run(h.handle("desconocido"))
