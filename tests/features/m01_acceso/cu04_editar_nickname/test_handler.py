"""CU-04 — Editar nickname."""
import asyncio

import pytest
from pydantic import ValidationError

from app.features.m01_acceso.cu04_editar_nickname.handler import EditarNicknameHandler
from app.features.m01_acceso.cu04_editar_nickname.request import EditarNicknameRequest
from app.shared.domain.errors import Conflicto
from tests.fakes import FakeAccountRepository, FakeClock, estudiante


def _escenario():
    repo = FakeAccountRepository()
    ana = asyncio.run(repo.crear(estudiante()))
    asyncio.run(repo.crear(estudiante(correo="beto@unas.edu.pe", nickname="beto_9")))
    return EditarNicknameHandler(repo, FakeClock()), repo, ana


def test_cambia_nickname_y_libera_el_anterior():
    h, repo, ana = _escenario()
    assert asyncio.run(h.handle(ana, EditarNicknameRequest(nickname="ana_nueva"))).nickname == "ana_nueva"
    assert not asyncio.run(repo.existe_por_nickname("ana_07"))  # RF-AUT-27
    assert repo.nickname_cambios == [(ana, "ana_nueva")]


def test_permite_cambiar_solo_mayusculas_del_propio():
    h, _, ana = _escenario()
    assert asyncio.run(h.handle(ana, EditarNicknameRequest(nickname="ANA_07"))).nickname == "ANA_07"


def test_rechaza_nickname_de_otro_sin_distinguir_mayusculas():
    h, _, ana = _escenario()
    with pytest.raises(Conflicto):
        asyncio.run(h.handle(ana, EditarNicknameRequest(nickname="BETO_9")))


def test_valida_formato():
    with pytest.raises(ValidationError):
        EditarNicknameRequest(nickname="con espacio")
