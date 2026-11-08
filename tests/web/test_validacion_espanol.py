"""RNF-USA-05: los errores de validación de la API se responden en español."""
import re

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.shared.db.mongo import get_database
from app.shared.security.session import SesionActual, get_sesion_actual
from app.shared.web.validacion import mensaje_en_espanol

INGLES = re.compile(r"\b(field|input|should|required|valid|value|error|be|must|least|most|characters)\b", re.I)


@pytest.fixture
def cliente():
    app.dependency_overrides[get_database] = lambda: None  # la validación falla antes de tocar la base
    app.dependency_overrides[get_sesion_actual] = lambda: SesionActual("s1", "u1", "ana_07")
    yield TestClient(app)
    app.dependency_overrides.clear()


CASOS = [
    ("post", "/api/publicaciones", {"json": {"titulo": "a", "descripcion": "b"}}, "El campo «tipo» es obligatorio"),
    ("post", "/api/publicaciones", {"json": {"tipo": "OTRO", "titulo": "a", "descripcion": "b"}},
     "El campo «tipo» admite solo: NECESITO, OFREZCO o ACTIVIDAD"),
    ("post", "/api/publicaciones", {"json": {"tipo": "OFREZCO", "titulo": "x" * 1001, "descripcion": "b"}},
     "El campo «título» admite como máximo 1000 caracteres"),
    ("get", "/api/feed?tipo=X", {}, "El campo «tipo» admite solo: NECESITO, OFREZCO o ACTIVIDAD"),
    ("post", "/api/cuentas", {"json": {}}, "El campo «correo» es obligatorio"),
    ("post", "/api/sesiones", {"json": {"correo": 5, "contrasena": "x"}}, "El campo «correo» debe ser un texto"),
    ("post", "/api/sesiones", {"content": b"{no es json", "headers": {"Content-Type": "application/json"}},
     "El cuerpo de la solicitud no es un JSON válido"),
    ("get", "/api/chats/c1?despues_de=ayer", {}, "El campo «fecha de referencia» debe ser una fecha y hora válida"),
    ("post", "/api/cuentas", {"json": {"correo": "a@unas.edu.pe", "contrasena": "clave123", "confirmacion": "otra123",
                                       "nickname": "ana_07", "acepta_terminos": True}},
     "Las contraseñas no coinciden"),  # validador propio: se conserva el mensaje del SRS
]


@pytest.mark.parametrize("metodo,ruta,kwargs,esperado", CASOS)
def test_errores_de_validacion_en_espanol(cliente, metodo, ruta, kwargs, esperado):
    respuesta = getattr(cliente, metodo)(ruta, **kwargs)
    datos = respuesta.json()
    assert respuesta.status_code == 422 and datos["codigo"] == "validacion"
    assert datos["detail"] == esperado
    for error in datos["errores"]:
        assert not INGLES.search(error["mensaje"]), error


def test_tipo_desconocido_tiene_mensaje_generico_en_espanol():
    assert mensaje_en_espanol({"type": "url_parsing", "loc": ("body", "x"), "msg": "Input should be a valid URL"}) \
        == "El campo «x» no es válido"
