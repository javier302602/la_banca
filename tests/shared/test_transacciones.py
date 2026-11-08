"""Reintento de transacciones ante TransientTransactionError (sin Mongo real)."""
import asyncio

import pytest
from pymongo.errors import DuplicateKeyError, OperationFailure

from app.shared.db import mongo


class SesionFalsa:
    def __init__(self, registro):
        self.registro = registro
        self.in_transaction = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    def start_transaction(self):
        self.in_transaction = True
        self.registro.append("inicio")

    async def commit_transaction(self):
        self.in_transaction = False
        self.registro.append("commit")

    async def abort_transaction(self):
        self.in_transaction = False
        self.registro.append("abort")


class ClienteFalso:
    def __init__(self):
        self.registro = []

    def start_session(self):
        async def abrir():
            return SesionFalsa(self.registro)

        return abrir()


class BaseFalsa:
    def __init__(self):
        self.client = ClienteFalso()


def conflicto_de_escritura():
    return OperationFailure("WriteConflict", 112, {"errorLabels": ["TransientTransactionError"]})


def test_reintenta_ante_write_conflict():
    db, llamadas = BaseFalsa(), []

    async def operacion(_):
        llamadas.append(1)
        if len(llamadas) < 3:
            raise conflicto_de_escritura()
        return "creada"

    assert asyncio.run(mongo.en_transaccion(db, operacion)) == "creada"
    assert len(llamadas) == 3
    assert db.client.registro == ["inicio", "abort", "inicio", "abort", "inicio", "commit"]


def test_se_rinde_tras_el_maximo_de_intentos():
    db = BaseFalsa()

    async def operacion(_):
        raise conflicto_de_escritura()

    with pytest.raises(OperationFailure):
        asyncio.run(mongo.en_transaccion(db, operacion, intentos=2))
    assert db.client.registro.count("inicio") == 2


def test_errores_no_transitorios_no_se_reintentan():
    db, llamadas = BaseFalsa(), []

    async def operacion(_):
        llamadas.append(1)
        raise DuplicateKeyError("duplicado")

    with pytest.raises(DuplicateKeyError):
        asyncio.run(mongo.en_transaccion(db, operacion))
    assert len(llamadas) == 1 and db.client.registro == ["inicio", "abort"]


def test_reintenta_el_commit_con_resultado_desconocido():
    db = BaseFalsa()
    fallos = []

    async def commit_inestable(self):
        if not fallos:
            fallos.append(1)
            raise OperationFailure("timeout", 50, {"errorLabels": ["UnknownTransactionCommitResult"]})
        self.in_transaction = False
        self.registro.append("commit")

    SesionFalsa.commit_transaction, original = commit_inestable, SesionFalsa.commit_transaction
    try:
        async def operacion(_):
            return 1

        assert asyncio.run(mongo.en_transaccion(db, operacion)) == 1
        assert db.client.registro == ["inicio", "commit"]
    finally:
        SesionFalsa.commit_transaction = original
