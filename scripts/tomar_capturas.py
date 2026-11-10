"""Capturas de las 15 páginas de La Banca en los anchos de diseño (360, 768 y 1024 px) con Playwright.

    python scripts/tomar_capturas.py --mongo-uri "mongodb://localhost:27017/?replicaSet=rs0&directConnection=true"

Vacía la base `la_banca_capturas`, arranca la app con uvicorn, siembra datos de ejemplo (tres cuentas,
publicaciones de los tres tipos y un chat con mensajes) y guarda una captura de página completa por página, ancho
y modo en docs/investigacion/capturas/<modo>/<nn>-<página>-<ancho>.png (modos: claro y oscuro, emulando
prefers-color-scheme). Requiere Playwright con Chromium.
"""
import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

ANCHOS = (360, 768, 1024)
TEMAS = {"claro": "light", "oscuro": "dark"}
ALTO = 800
CLAVE = "clave123"
CUENTAS = {"ana": ("ana@unas.edu.pe", "ana_07"), "beto": ("beto@unas.edu.pe", "beto_9"),
           "caro": ("caro@unas.edu.pe", "caro_3")}


def paginas(d: dict) -> list[tuple[str, str, str | None, str]]:
    """(nombre, ruta, cuenta con sesión o None, selector que indica que la página cargó)."""
    return [
        ("login", "/login", None, "#form-login"),
        ("registro", "/registro", None, "#form-registro"),
        ("activar", "/activar", None, "#form-reenvio"),
        ("recuperar", "/recuperar", None, "#form-recuperar"),
        ("restablecer", "/restablecer?token=ejemplo", None, "#form-restablecer"),
        ("terminos", "/terminos", None, "article"),
        ("feed", "/feed", "ana", ".tarjeta-publicacion"),
        ("detalle", f"/publicaciones/{d['ajena']}", "ana", "#detalle:not(.d-none)"),
        ("crear-publicacion", "/publicaciones/nueva", "ana", "#cupo:not(:empty)"),
        ("mis-publicaciones", "/publicaciones/mias", "ana", "#lista li"),
        ("mis-chats", "/chats", "ana", "#lista a"),
        ("chat", f"/chats/{d['chat']}", "ana", "#historial .burbuja"),
        ("responder", f"/publicaciones/{d['para_responder']}/responder", "ana", "#form-mensaje"),
        ("reportar", f"/publicaciones/{d['ajena']}/reportar", "ana", "#form-reporte"),
        ("perfil", "/perfil", "ana", "#form-nickname"),
    ]


def _puerto() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def arrancar(uri: str, base: str, registro: Path) -> tuple[subprocess.Popen, str]:
    puerto = _puerto()
    url = f"http://127.0.0.1:{puerto}"
    entorno = {**os.environ, "MONGO_URI": uri, "MONGO_DB": base, "DOMINIO_INSTITUCIONAL": "unas.edu.pe",
               "COOKIE_SECURE": "false", "EMAIL_SENDER": "consola", "IMAGE_STORAGE": "memoria",
               "ENTORNO": "desarrollo", "APP_BASE_URL": url, "TERMINOS_VERSION": "1.0",
               "TERMINOS_FECHA": "2026-11-01", "CANAL_ARCO": "datospersonales@unas.edu.pe"}
    with open(registro, "wb") as salida:
        proceso = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                                    "--port", str(puerto), "--log-level", "warning"],
                                   cwd=RAIZ, env=entorno, stdout=salida, stderr=subprocess.STDOUT)
    for _ in range(150):
        try:
            with urllib.request.urlopen(f"{url}/login", timeout=2):
                return proceso, url
        except OSError:
            time.sleep(0.2)
    proceso.kill()
    raise RuntimeError(f"la app no arrancó; ver {registro}")


def sembrar(db, url: str, navegador) -> dict:
    from app.shared.db.mapeo import estudiante_a_doc
    from app.shared.domain.entities import AceptacionTerminos, EnlaceUnUso, EstadoCuenta, Estudiante
    from app.shared.security.hashing import BcryptPasswordHasher

    ahora = datetime.now(timezone.utc)
    hash_ = BcryptPasswordHasher(costo=4).hash(CLAVE)
    for correo, nick in CUENTAS.values():
        db.accounts.insert_one(estudiante_a_doc(Estudiante(
            "", correo, hash_, nick, EstadoCuenta.ACTIVA, ahora, AceptacionTerminos("1.0", ahora),
            activacion=EnlaceUnUso(None, None, [ahora]), fecha_activacion=ahora)))
    sesiones = {}
    for clave, (correo, _) in CUENTAS.items():
        sesiones[clave] = navegador.new_context(base_url=url)
        sesiones[clave].request.post("/api/sesiones", data={"correo": correo, "contrasena": CLAVE})

    def publicar(quien, tipo, titulo, descripcion):
        r = sesiones[quien].request.post("/api/publicaciones", data={"tipo": tipo, "titulo": titulo,
                                                                     "descripcion": descripcion})
        return r.json()["id"]

    publicar("ana", "OFREZCO", "Presto calculadora científica", "Una Casio fx-991, en la biblioteca hasta las 6 pm.")
    ajena = publicar("beto", "NECESITO", "Busco grupo para estudiar Física II",
                     "Examen el viernes. Somos dos, nos falta una persona para resolver la práctica 4.")
    para_responder = publicar("caro", "ACTIVIDAD", "Partido de vóley en la loza deportiva",
                              "Faltan 3 personas, empezamos a las 5:30 pm. Traigan agua.")
    publicar("beto", "OFREZCO", "Apuntes de Diseño Detallado de Software",
             "Tengo los apuntes de la unidad II completos; los presto para fotocopiar.")
    chat = sesiones["ana"].request.post(f"/api/publicaciones/{ajena}/respuestas",
                                        multipart={"texto": "Hola, me sumo al grupo. ¿Dónde se reúnen?"}).json()["chat_id"]
    for quien, texto in (("beto", "¡Genial! En la sala 2 de la biblioteca."), ("beto", "A las 4 pm, ¿te parece?"),
                         ("ana", "Perfecto, allí estaré."), ("ana", "Llevo la práctica impresa.")):
        sesiones[quien].request.post(f"/api/chats/{chat}/mensajes", multipart={"texto": texto})
    for contexto in sesiones.values():
        contexto.close()
    return {"ajena": ajena, "para_responder": para_responder, "chat": chat}


def capturar(uri: str, salida: Path, anchos=ANCHOS, base: str = "la_banca_capturas",
             temas=tuple(TEMAS)) -> list[Path]:
    from playwright.sync_api import sync_playwright
    from pymongo import MongoClient

    salida.mkdir(parents=True, exist_ok=True)
    cliente = MongoClient(uri)
    cliente.drop_database(base)
    proceso, url = arrancar(uri, base, salida / "uvicorn.log")
    archivos = []
    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch()
            datos = sembrar(cliente[base], url, navegador)
            for tema, esquema in ((t, TEMAS[t]) for t in temas):
              (salida / tema).mkdir(parents=True, exist_ok=True)
              for ancho in anchos:
                for n, (nombre, ruta, cuenta, listo) in enumerate(paginas(datos), start=1):
                    contexto = navegador.new_context(base_url=url, viewport={"width": ancho, "height": ALTO},
                                                     locale="es-PE", timezone_id="America/Lima",
                                                     color_scheme=esquema)
                    if cuenta:
                        contexto.request.post("/api/sesiones", data={"correo": CUENTAS[cuenta][0], "contrasena": CLAVE})
                    pagina = contexto.new_page()
                    pagina.goto(ruta)
                    pagina.locator(listo).first.wait_for(timeout=15_000)
                    pagina.wait_for_timeout(300)  # fin de transiciones
                    archivo = salida / tema / f"{n:02d}-{nombre}-{ancho}.png"
                    pagina.screenshot(path=str(archivo), full_page=True)
                    archivos.append(archivo)
                    contexto.close()
            navegador.close()
    finally:
        proceso.terminate()
        proceso.wait(timeout=10)
        cliente.drop_database(base)
        (salida / "uvicorn.log").unlink(missing_ok=True)
    return archivos


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mongo-uri", default=os.environ.get(
        "E2E_MONGO_URI", "mongodb://localhost:27017/?replicaSet=rs0&directConnection=true"))
    parser.add_argument("--salida", default=str(RAIZ / "docs" / "investigacion" / "capturas"))
    parser.add_argument("--anchos", default=",".join(map(str, ANCHOS)))
    parser.add_argument("--temas", default=",".join(TEMAS))
    args = parser.parse_args()
    archivos = capturar(args.mongo_uri, Path(args.salida), tuple(int(a) for a in args.anchos.split(",")),
                        temas=tuple(args.temas.split(",")))
    print(f"{len(archivos)} capturas en {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
