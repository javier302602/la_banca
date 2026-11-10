"""Fase 6 — prueba completa de respaldo y restauración con Docker (SRS v2.0, cambios 6.1–6.3).

1. Levanta un compose «origen», crea usuarios, foto de perfil, publicación con imágenes y un chat con texto,
   imagen, sticker y documento; ejecuta scripts/backup.sh.
2. Levanta un compose «destino» limpio (volúmenes nuevos), ejecuta scripts/restore.sh y verifica que usuarios
   (con sus contraseñas), chats, mensajes y archivos (byte a byte) estén íntegros.
3. Genera un respaldo REAL de la v1: ejecuta el código del tag v1.0.0 (git worktree) contra un MongoDB, lo vuelca con
   mongodump como lo hacía la v1, lo restaura sobre la v2 y verifica que la migración 001 lo convierta.

Requiere Docker, la imagen de la app construida (docker compose build) y el MongoDB de pruebas de E2E_MONGO_URI
(para el paso 3). Es lenta (varios minutos): solo corre con PRUEBA_DOCKER=1.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
TMP = RAIZ / ".tmp-pruebas"
CLAVE = "Respaldo123!"

pytestmark = pytest.mark.skipif(os.environ.get("PRUEBA_DOCKER") != "1", reason="solo con PRUEBA_DOCKER=1")


def bash() -> str:
    if sys.platform == "win32":
        for carpeta in Path(shutil.which("git")).resolve().parents:
            if (carpeta / "bin" / "bash.exe").exists():
                return str(carpeta / "bin" / "bash.exe")
    return shutil.which("bash")


def correr(*args, entrada=None, env=None, cwd=RAIZ, timeout=600) -> str:
    r = subprocess.run(args, cwd=cwd, capture_output=True, input=entrada, timeout=timeout,
                       env={**os.environ, "MSYS_NO_PATHCONV": "1", **(env or {})})
    assert r.returncode == 0, (args, r.stdout.decode(errors="replace")[-3000:], r.stderr.decode(errors="replace")[-3000:])
    return r.stdout.decode(errors="replace")


class Pila:
    """Un docker compose aislado (proyecto, puertos, volúmenes y archivo .env propios)."""

    def __init__(self, nombre: str, desplazamiento: int):
        self.nombre, self.puerto = nombre, 18443 + desplazamiento
        self.env = TMP / f"{nombre}.env"
        base = (RAIZ / ".env.example").read_text(encoding="utf-8")
        extra = {"COMPOSE_PROFILES": "", "PUERTO_HTTP": 18080 + desplazamiento, "PUERTO_HTTPS": self.puerto,
                 "PUERTO_CONSOLA_MINIO": 19001 + desplazamiento, "APP_BASE_URL": f"https://localhost:{self.puerto}",
                 "EMAIL_SENDER": "consola", "STORAGE_ACCESS_KEY": "respaldo", "STORAGE_SECRET_KEY": "RespaldoSecreto9",
                 "CRON_SECRET": "secreto-de-prueba", "ARCHIVO_ENV": f".tmp-pruebas/{nombre}.env", "WEB_WORKERS": 2}
        lineas = [linea for linea in base.splitlines() if linea.split("=", 1)[0] not in extra]
        self.env.write_text("\n".join(lineas + [f"{k}={v}" for k, v in extra.items()]) + "\n", encoding="utf-8")
        self.compose = f"docker compose -p {nombre} --env-file .tmp-pruebas/{nombre}.env"
        self.url = f"https://localhost:{self.puerto}"

    def dc(self, *args, **kw) -> str:
        return correr(*self.compose.split(), *args, **kw)

    def subir(self):
        self.dc("up", "-d", "--wait", timeout=900)

    def bajar(self):
        subprocess.run([*self.compose.split(), "down", "-v", "--remove-orphans"], cwd=RAIZ, capture_output=True,
                       env={**os.environ, "MSYS_NO_PATHCONV": "1"}, timeout=300)

    def script(self, *args) -> str:
        return correr(bash(), *args, env={"COMPOSE": self.compose}, timeout=900)

    def crear_usuario(self, correo, nick):
        self.dc("exec", "-T", "-e", f"NUEVA_CONTRASENA={CLAVE}", "app", "python", "-m", "scripts.crear_usuario",
                "--correo", correo, "--nickname", nick)

    def cliente(self, correo=None):
        import httpx

        c = httpx.Client(base_url=self.url, verify=False, timeout=30)
        if correo:
            r = c.post("/api/sesiones", json={"correo": correo, "contrasena": CLAVE})
            assert r.status_code == 200, r.text
        return c

    def conteos(self) -> dict:
        salida = self.dc("exec", "-T", "mongo", "mongosh", "--quiet", "la_banca_db", "--eval",
                         "print(JSON.stringify(Object.fromEntries(db.getCollectionNames().map(c => "
                         "[c, db.getCollection(c).countDocuments()]))))")
        return json.loads(salida.strip().splitlines()[-1])


def sha(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def png(color) -> bytes:
    import io

    from PIL import Image

    salida = io.BytesIO()
    Image.new("RGB", (120, 90), color).save(salida, format="PNG")
    return salida.getvalue()


PDF = b"%PDF-1.4\n% respaldo\n1 0 obj<<>>endobj\n%%EOF\n"


@pytest.fixture(scope="module")
def pilas():
    TMP.mkdir(exist_ok=True)
    origen, destino = Pila("lbp-origen", 0), Pila("lbp-destino", 100)
    yield origen, destino
    for p in (origen, destino):
        p.bajar()


def test_respaldo_en_un_contenedor_y_restauracion_en_otro_limpio(pilas):
    origen, destino = pilas
    origen.bajar()
    origen.subir()
    origen.crear_usuario("ana.respaldo@unas.edu.pe", "ana_respaldo")
    origen.crear_usuario("beto.respaldo@unas.edu.pe", "beto_respaldo")
    a, b = origen.cliente("ana.respaldo@unas.edu.pe"), origen.cliente("beto.respaldo@unas.edu.pe")
    assert a.patch("/api/cuentas/me/perfil", json={"biografia": "Respaldada", "avatar": "avatar-05"}).status_code == 200
    foto = a.put("/api/cuentas/me/foto", files={"foto": ("yo.png", png("teal"), "image/png")}).json()["apariencia"]["url"]
    r = a.post("/api/publicaciones", data={"tipo": "OFREZCO", "titulo": "Calculadora", "descripcion": "Respaldo"},
               files=[("imagenes", ("1.png", png("red"), "image/png")), ("imagenes", ("2.png", png("blue"), "image/png"))])
    assert r.status_code == 201, r.text
    pid, galeria = r.json()["id"], r.json()["imagenes"]
    chat = b.post(f"/api/publicaciones/{pid}/respuestas", data={"texto": "¿Sigue disponible? 👍"}).json()["chat_id"]
    assert b.post(f"/api/chats/{chat}/mensajes", files={"imagen": ("c.png", png("green"), "image/png")}).status_code == 201
    assert b.post(f"/api/chats/{chat}/mensajes", data={"sticker": "sticker-17"}).status_code == 201
    doc = b.post(f"/api/chats/{chat}/mensajes", files={"documento": ("guía.pdf", PDF, "application/pdf")}).json()["documento"]
    assert a.post(f"/api/chats/{chat}/mensajes", data={"texto": "Sí, mañana"}).status_code == 201
    original = a.get(f"/api/chats/{chat}").json()
    huellas = {"foto": sha(a.get(foto).content), "documento": sha(a.get(doc["url"]).content),
               "galeria": [sha(a.get(u).content) for u in galeria],
               "imagen_chat": sha(a.get(next(m["imagen_url"] for m in original["mensajes"] if m["imagen_url"])).content)}
    assert huellas["documento"] == sha(PDF)
    conteos = origen.conteos()

    salida = origen.script("scripts/backup.sh")
    paquete = salida.strip().splitlines()[-1].split("Respaldo listo: ")[1].split(" (")[0]
    assert "(5 archivos)" in salida  # foto + 2 de la galería + imagen del chat + documento

    destino.bajar()
    destino.subir()
    assert destino.cliente().post("/api/sesiones", json={"correo": "ana.respaldo@unas.edu.pe",
                                                         "contrasena": CLAVE}).status_code == 401  # está vacío
    destino.script("scripts/restore.sh", paquete, "--si")

    assert destino.conteos() == conteos
    a2, b2 = destino.cliente("ana.respaldo@unas.edu.pe"), destino.cliente("beto.respaldo@unas.edu.pe")
    perfil = b2.get("/api/perfiles/ana_respaldo").json()
    assert perfil["biografia"] == "Respaldada" and sha(b2.get(perfil["apariencia"]["url"]).content) == huellas["foto"]
    detalle = b2.get(f"/api/publicaciones/{pid}").json()
    assert [sha(b2.get(u).content) for u in detalle["imagenes"]] == huellas["galeria"]
    restaurado = a2.get(f"/api/chats/{chat}").json()
    assert [(m["texto"], m["sticker"], bool(m["imagen_url"]), bool(m["documento"])) for m in restaurado["mensajes"]] == \
           [(m["texto"], m["sticker"], bool(m["imagen_url"]), bool(m["documento"])) for m in original["mensajes"]]
    assert sha(a2.get(next(m["imagen_url"] for m in restaurado["mensajes"] if m["imagen_url"])).content) == huellas["imagen_chat"]
    documento = next(m["documento"] for m in restaurado["mensajes"] if m["documento"])
    assert documento["nombre"] == "guía.pdf" and sha(b2.get(documento["url"]).content) == huellas["documento"]
    assert "aplicada" in destino.dc("exec", "-T", "app", "python", "-m", "scripts.migrar", "--estado")
    origen.bajar()


V1_GENERAR = r'''
import json, os
from fastapi.testclient import TestClient
from app.main import app
from app.shared.email.sender import get_email_sender

def cuenta(c, correo, nick):
    r = c.post("/api/cuentas", json={"correo": correo, "contrasena": "clave1234", "confirmacion": "clave1234",
                                     "nickname": nick, "acepta_terminos": True})
    assert r.status_code == 201, r.text
    token = get_email_sender().enviados[-1].enlace.split("token=")[1]
    assert c.post("/api/cuentas/activar", json={"token": token}).status_code == 200
    assert c.post("/api/sesiones", json={"correo": correo, "contrasena": "clave1234"}).status_code == 200

with TestClient(app, base_url="https://testserver") as a, TestClient(app, base_url="https://testserver") as b:
    cuenta(a, "ana.v1@unas.edu.pe", "ana_v1")
    cuenta(b, "beto.v1@unas.edu.pe", "beto_v1")
    pid = a.post("/api/publicaciones", json={"tipo": "NECESITO", "titulo": "Apuntes v1", "descripcion": "De la v1"}).json()["id"]
    chat = b.post(f"/api/publicaciones/{pid}/respuestas", data={"texto": "Te los presto"}).json()["chat_id"]
    assert a.post(f"/api/chats/{chat}/mensajes", data={"texto": "Gracias"}).status_code == 201
    print(json.dumps({"pid": pid, "chat": chat}))
'''


def test_respaldo_de_v1_se_restaura_sobre_v2(pilas, tmp_path):
    _, destino = pilas
    uri = os.environ.get("E2E_MONGO_URI")
    if not uri:
        pytest.skip("E2E_MONGO_URI: MongoDB de pruebas para ejecutar el código de la v1")
    contenedor = os.environ.get("E2E_MONGO_CONTENEDOR", "la-banca-pruebas")
    v1 = TMP / "v1"
    if not v1.exists():
        correr("git", "worktree", "add", "--detach", str(v1), "v1.0.0")
    try:
        from pymongo import MongoClient

        MongoClient(uri).drop_database("la_banca_v1")
        env = {"MONGO_URI": uri, "MONGO_DB": "la_banca_v1", "ENTORNO": "desarrollo", "IMAGE_STORAGE": "memoria",
               "EMAIL_SENDER": "consola", "DOMINIO_INSTITUCIONAL": "unas.edu.pe", "APP_BASE_URL": "https://testserver",
               "PYTHONPATH": str(v1), "PYTHONUTF8": "1"}
        ids = json.loads(correr(sys.executable, "-c", V1_GENERAR, cwd=v1, env=env).strip().splitlines()[-1])
        # Respaldo exactamente como lo hacía la v1 (scripts/respaldo_mongodb.py): mongodump --gzip --archive
        archivo = TMP / "la_banca_v1-20261101T120000Z.archive.gz"
        r = subprocess.run(["docker", "exec", contenedor, "mongodump", "--quiet", "--db=la_banca_v1", "--gzip",
                            "--archive"], capture_output=True, timeout=300)
        assert r.returncode == 0, r.stderr
        archivo.write_bytes(r.stdout)
        cuenta_v1 = MongoClient(uri).la_banca_v1.accounts.find_one({"nickname": "ana_v1"})
        assert "bio" not in cuenta_v1 and "avatar" not in cuenta_v1  # de verdad es un documento de v1
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(v1)], cwd=RAIZ, capture_output=True)

    destino.bajar()
    destino.subir()
    destino.script("scripts/restore.sh", str(archivo.relative_to(RAIZ)).replace("\\", "/"), "--si")

    assert "aplicada   001_v1_a_v2" in destino.dc("exec", "-T", "app", "python", "-m", "scripts.migrar", "--estado")
    conv = json.loads(destino.dc("exec", "-T", "mongo", "mongosh", "--quiet", "la_banca_db", "--eval",
                                 "print(JSON.stringify(db.accounts.findOne({nickname: 'ana_v1'}, {bio: 1, avatar: 1, photo: 1, _id: 0})))"
                                 ).strip().splitlines()[-1])
    assert conv == {"bio": "", "avatar": None, "photo": None}
    # Las cuentas de v1 inician sesión con su contraseña de siempre y su contenido se ve en la v2
    import httpx

    with httpx.Client(base_url=destino.url, verify=False, timeout=30) as a:
        assert a.post("/api/sesiones", json={"correo": "ana.v1@unas.edu.pe", "contrasena": "clave1234"}).status_code == 200
        feed = a.get("/api/feed").json()["items"]
        item = next(i for i in feed if i["id"] == ids["pid"])
        assert item["num_imagenes"] == 0 and item["apariencia_autor"]["tipo"] == "iniciales"
        chat = a.get(f"/api/chats/{ids['chat']}").json()
        assert [m["texto"] for m in chat["mensajes"]] == ["Te los presto", "Gracias"]
        assert all(m["sticker"] is None and m["documento"] is None for m in chat["mensajes"])
        assert a.patch("/api/cuentas/me/perfil", json={"biografia": "Ahora en v2", "avatar": "avatar-02"}).status_code == 200
