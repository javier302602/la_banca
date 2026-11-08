"""CU-16 — Consultar términos de uso y política de privacidad."""
import asyncio

from fastapi.testclient import TestClient

from app.features.m01_acceso.cu16_consultar_terminos.handler import ConsultarTerminosHandler
from app.features.m01_acceso.cu16_consultar_terminos.repository import leer_terminos


def test_devuelve_version_fecha_y_texto():
    r = asyncio.run(ConsultarTerminosHandler("1.0", "2026-10-01", lambda: "texto").handle())
    assert (r.version, r.fecha, r.texto) == ("1.0", "2026-10-01", "texto")


def test_sin_version_configurada_queda_pendiente():
    r = asyncio.run(ConsultarTerminosHandler(None, "", lambda: "t").handle())
    assert r.version == r.fecha == "pendiente"


def test_texto_incluye_datos_tratados_y_api_sin_sesion():
    assert "Correo institucional" in leer_terminos()
    from app.main import app

    respuesta = TestClient(app).get("/api/terminos")  # sin sesión (RF-AUT-18)
    assert respuesta.status_code == 200 and "texto" in respuesta.json()
