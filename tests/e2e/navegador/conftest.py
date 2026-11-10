"""Pruebas en navegador real con Playwright contra la app servida por uvicorn y un MongoDB replica set.

Forman parte de `pytest -m e2e` (están bajo tests/e2e). Requieren:
- MongoDB replica set en E2E_MONGO_URI (por defecto localhost:27017, rs0);
- Playwright con sus navegadores: `pip install -r requirements-dev.txt` y `python -m playwright install`.
Si falta algo, se omiten.

NAVEGADORES elige los motores, separados por comas; por defecto los tres (RNF-COM-01): chromium,firefox,webkit.
"""
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from tests.e2e.conftest import URI_POR_DEFECTO

RAIZ = Path(__file__).resolve().parents[3]
BASE = "la_banca_navegador"
CLAVE = "clave123"
NAVEGADORES = [n.strip() for n in os.environ.get("NAVEGADORES", "chromium,firefox,webkit").split(",") if n.strip()]


@pytest.fixture(scope="session")
def base_navegador():
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError

    uri = os.environ.get("E2E_MONGO_URI", URI_POR_DEFECTO)
    cliente = MongoClient(uri, serverSelectionTimeoutMS=3000)
    try:
        cliente.admin.command("ping")
    except PyMongoError as error:
        pytest.skip(f"MongoDB de pruebas no disponible en {uri}: {error}")
    cliente.drop_database(BASE)
    yield cliente[BASE], uri
    cliente.drop_database(BASE)


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def registro_servidor(tmp_path_factory) -> Path:
    """Archivo con el registro técnico de uvicorn (incluye los correos de desarrollo con sus enlaces)."""
    return tmp_path_factory.mktemp("servidor") / "uvicorn.log"


@pytest.fixture(scope="session")
def servidor(base_navegador, registro_servidor):
    _, uri = base_navegador
    puerto = _puerto_libre()
    url = f"http://127.0.0.1:{puerto}"
    entorno = {**os.environ, "MONGO_URI": uri, "MONGO_DB": BASE, "DOMINIO_INSTITUCIONAL": "unas.edu.pe",
               "COOKIE_SECURE": "false", "EMAIL_SENDER": "consola", "IMAGE_STORAGE": "memoria",
               "ENTORNO": "desarrollo", "CRON_SECRET": "s3cr3t", "APP_BASE_URL": url,
               "TERMINOS_VERSION": "1.0", "TERMINOS_FECHA": "2026-11-01", "CANAL_ARCO": "datospersonales@unas.edu.pe"}
    # A un archivo y no a una tubería: una tubería sin leer se llena y bloquea al servidor
    with open(registro_servidor, "wb") as salida:
        proceso = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                                    "--port", str(puerto), "--log-level", "warning"],
                                   cwd=RAIZ, env=entorno, stdout=salida, stderr=subprocess.STDOUT)
    limite = time.monotonic() + 30
    while True:
        try:
            with urllib.request.urlopen(f"{url}/login", timeout=2) as r:
                if r.status == 200:
                    break
        except OSError:
            pass
        if proceso.poll() is not None or time.monotonic() > limite:
            proceso.kill()
            pytest.fail(f"uvicorn no arrancó: {registro_servidor.read_text(errors='replace')[-2000:]}")
        time.sleep(0.2)
    yield url
    proceso.terminate()
    proceso.wait(timeout=10)


def ultimo_enlace(registro: Path, ruta: str) -> str:
    """Último enlace (/activar o /restablecer) que el emisor de correo de desarrollo dejó en el registro."""
    limite = time.monotonic() + 10
    while time.monotonic() < limite:
        enlaces = [linea.rsplit("-> ", 1)[1].strip() for linea in registro.read_text(errors="replace").splitlines()
                   if "[correo de desarrollo]" in linea and f"{ruta}?token=" in linea]
        if enlaces:
            return enlaces[-1]
        time.sleep(0.2)
    raise AssertionError(f"No se envió ningún enlace {ruta}")


@pytest.fixture(scope="session")
def usuarios(base_navegador, servidor):
    """Cuentas activas creadas directamente en la base (el registro se prueba en otros tests)."""
    from datetime import datetime, timezone

    from app.shared.db.mapeo import estudiante_a_doc
    from app.shared.domain.entities import AceptacionTerminos, EnlaceUnUso, EstadoCuenta, Estudiante
    from app.shared.security.hashing import BcryptPasswordHasher

    db, _ = base_navegador
    hash_ = BcryptPasswordHasher(costo=4).hash(CLAVE)  # costo bajo solo para acelerar las pruebas
    ahora = datetime.now(timezone.utc)
    cuentas = {"ana": ("ana@unas.edu.pe", "ana_07"), "beto": ("beto@unas.edu.pe", "beto_9"),
               "caro": ("caro@unas.edu.pe", "caro_3")}
    for correo, nick in cuentas.values():
        doc = estudiante_a_doc(Estudiante("", correo, hash_, nick, EstadoCuenta.ACTIVA, ahora,
                                          AceptacionTerminos("1.0", ahora),
                                          activacion=EnlaceUnUso(None, None, [ahora]),  # el envío del registro
                                          fecha_activacion=ahora))
        db.accounts.replace_one({"email": correo}, doc, upsert=True)
    return cuentas


# Alcance de módulo: la API síncrona de Playwright mantiene un event loop en el hilo principal mientras
# está abierta, y los demás e2e usan asyncio.run(); se cierra al terminar cada archivo de pruebas.
@pytest.fixture(scope="module")
def playwright_sync():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        yield p


@pytest.fixture(scope="module", params=NAVEGADORES)
def navegador(request, playwright_sync):
    try:
        browser = getattr(playwright_sync, request.param).launch()
    except Exception as error:  # navegador no instalado
        pytest.skip(f"{request.param} no disponible: {str(error).splitlines()[0]}")
    yield browser
    browser.close()


@pytest.fixture(scope="module", autouse=True)
def _datos_limpios(navegador, base_navegador):
    """Cada archivo de pruebas y cada navegador empiezan sin publicaciones, chats, reportes ni sesiones
    (las cuentas se conservan): así el límite de publicaciones activas no depende del orden de ejecución."""
    db, _ = base_navegador
    for coleccion in ("publications", "chats", "messages", "reports", "sessions", "login_attempts"):
        db[coleccion].delete_many({})


@pytest.fixture
def contexto(navegador, servidor):
    ctx = navegador.new_context(base_url=servidor, locale="es-PE", timezone_id="America/Lima")
    ctx.set_default_timeout(10_000)
    yield ctx
    ctx.close()


@pytest.fixture
def pagina(contexto):
    return contexto.new_page()


def iniciar_sesion(contexto, correo: str) -> None:
    """Inicia sesión por la API: la cookie queda en el contexto del navegador."""
    r = contexto.request.post("/api/sesiones", data={"correo": correo, "contrasena": CLAVE})
    assert r.ok, r.text()


def png(color=(60, 120, 200), tamano=(480, 320)) -> bytes:
    import io

    from PIL import Image

    salida = io.BytesIO()
    Image.new("RGB", tamano, color).save(salida, format="PNG")
    return salida.getvalue()


def multipart(campos, archivos) -> tuple[bytes, str]:
    """Cuerpo multipart/form-data con campos repetidos (la opción multipart= de Playwright usa un dict)."""
    import uuid

    limite = uuid.uuid4().hex
    crlf = "\r\n"
    partes = []
    for nombre, valor in campos:
        partes.append(f'--{limite}{crlf}Content-Disposition: form-data; name="{nombre}"{crlf}{crlf}{valor}{crlf}'
                      .encode())
    for nombre, archivo, contenido in archivos:
        cabecera = (f'--{limite}{crlf}Content-Disposition: form-data; name="{nombre}"; filename="{archivo}"{crlf}'
                    f"Content-Type: application/octet-stream{crlf}{crlf}")
        partes.append(cabecera.encode() + contenido + crlf.encode())
    partes.append(f"--{limite}--{crlf}".encode())
    return b"".join(partes), f"multipart/form-data; boundary={limite}"


def publicar(contexto, titulo: str = "Apuntes de cálculo", tipo: str = "OFREZCO", imagenes: int = 0) -> str:
    if imagenes:  # SRS v2.0: multipart con hasta 3 imágenes (el campo «imagenes» se repite)
        campos = [("tipo", tipo), ("titulo", titulo), ("descripcion", "Los presto")]
        colores = [(60, 120, 200), (200, 90, 60), (60, 160, 90)]
        archivos = [("imagenes", f"foto{i}.png", png(colores[i % 3])) for i in range(imagenes)]
        cuerpo, tipo_contenido = multipart(campos, archivos)
        r = contexto.request.post("/api/publicaciones", data=cuerpo, headers={"Content-Type": tipo_contenido})
        assert r.ok, r.text()
        return r.json()["id"]
    r = contexto.request.post("/api/publicaciones", data={"tipo": tipo, "titulo": titulo, "descripcion": "Los presto"})
    assert r.ok, r.text()
    return r.json()["id"]


def responder(contexto, publicacion_id: str, texto: str = "Hola, ¿sigue disponible?") -> str:
    r = contexto.request.post(f"/api/publicaciones/{publicacion_id}/respuestas", multipart={"texto": texto})
    assert r.ok, r.text()
    return r.json()["chat_id"]
