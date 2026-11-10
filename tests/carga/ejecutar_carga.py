"""Ejecuta la prueba de carga completa de RNF-REN-01 a RNF-REN-06 y deja un resumen en JSON.

    python tests/carga/ejecutar_carga.py --mongo-uri "mongodb://localhost:27018/?replicaSet=rs0&directConnection=true"

Pasos:
1. Vacía la base de carga y arranca la app con uvicorn (--workers, por defecto 4).
2. Siembra 10 000 cuentas activas y 3 000 publicaciones activas (PA-35, RNF-REN-06).
3. Corre Locust sin interfaz: 100 usuarios durante 15 min con el perfil de RNF-REN-01 (locustfile.py).
4. Con un solo worker (las imágenes se guardan en memoria del proceso) mide:
   - RNF-REN-04: 20 imágenes JPEG de ~5 MB, desde el envío hasta que el otro participante las descarga, y suma
     el tiempo de transferencia de subida y bajada en una red de 10 Mbps (no se emula la red en local);
   - RNF-REN-05: 100 registros; el correo de activación se entrega al emisor dentro de la propia solicitud,
     así que su duración es una cota superior del tiempo hasta dejarlo en cola.
5. Compara los p95 con los límites del SRS (perfil.evaluar) y escribe resultados/resumen.json.
"""
import argparse
import csv
import io
import json
import os
import random
import socket
import statistics
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import perfil  # noqa: E402

CLAVE = "clave123"


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def arrancar_app(uri: str, base: str, workers: int, registro: Path) -> tuple[subprocess.Popen, str]:
    puerto = _puerto_libre()
    url = f"http://127.0.0.1:{puerto}"
    entorno = {**os.environ, "MONGO_URI": uri, "MONGO_DB": base, "DOMINIO_INSTITUCIONAL": "unas.edu.pe",
               "COOKIE_SECURE": "false", "EMAIL_SENDER": "consola", "IMAGE_STORAGE": "memoria",
               "ENTORNO": "desarrollo", "APP_BASE_URL": url, "CRON_SECRET": "carga"}
    with open(registro, "ab") as salida:
        proceso = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                                    "--port", str(puerto), "--workers", str(workers), "--log-level", "warning"],
                                   cwd=RAIZ, env=entorno, stdout=salida, stderr=subprocess.STDOUT)
    limite = time.monotonic() + 60
    while time.monotonic() < limite:
        try:
            with urllib.request.urlopen(f"{url}/login", timeout=2):
                return proceso, url
        except OSError:
            time.sleep(0.3)
    proceso.kill()
    raise RuntimeError("la app no arrancó; ver " + str(registro))


def detener(proceso: subprocess.Popen) -> None:
    proceso.terminate()
    try:
        proceso.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proceso.kill()


def sembrar(db) -> tuple[int, int]:
    """10 000 cuentas activas (carga00000…) y 3 000 publicaciones activas de las cuentas 0–999."""
    from app.shared.db.mapeo import estudiante_a_doc, publicacion_a_doc
    from app.shared.domain.entities import (AceptacionTerminos, EnlaceUnUso, EstadoCuenta, Estudiante, Publicacion,
                                            TipoPublicacion)
    from app.shared.security.hashing import BcryptPasswordHasher

    ahora = datetime.now(timezone.utc)
    hash_ = BcryptPasswordHasher().hash(CLAVE)  # costo real (12): la verificación pesa como en producción
    cuentas = []
    for n in range(perfil.CUENTAS_REGISTRADAS):
        cuentas.append(estudiante_a_doc(Estudiante(
            "", f"carga{n:05d}@unas.edu.pe", hash_, f"carga{n:05d}", EstadoCuenta.ACTIVA, ahora - timedelta(days=1),
            AceptacionTerminos("1.0", ahora), activacion=EnlaceUnUso(None, None, [ahora - timedelta(days=1)]),
            fecha_activacion=ahora)))
    ids = db.accounts.insert_many(cuentas).inserted_ids
    tipos = list(TipoPublicacion)
    publicaciones = []
    for i in range(perfil.PUBLICACIONES_ACTIVAS):
        creada = ahora - timedelta(seconds=random.randint(0, 22 * 3600))  # vigentes durante toda la prueba
        publicaciones.append(publicacion_a_doc(Publicacion(
            "", str(ids[i // 3]), f"carga{i // 3:05d}", tipos[i % 3], f"Publicación sembrada {i}",
            "Texto de una publicación sembrada para la prueba de carga", creada, creada + timedelta(hours=24))))
    db.publications.insert_many(publicaciones)
    return db.accounts.count_documents({}), db.publications.count_documents({"status": "ACTIVE",
                                                                             "expiresAt": {"$gt": ahora}})


def correr_locust(url: str, usuarios: int, duracion: str, prefijo: Path) -> dict:
    subprocess.run([sys.executable, "-m", "locust", "-f", str(Path(__file__).with_name("locustfile.py")),
                    "--headless", "-u", str(usuarios), "-r", "10", "--run-time", duracion, "--host", url,
                    "--csv", str(prefijo), "--only-summary", "--stop-timeout", "25"], cwd=RAIZ, check=False,
                   env={**os.environ, "PYTHONUTF8": "1"})  # en Windows, CSV en UTF-8 (nombres con tildes)
    filas = list(csv.DictReader(open(f"{prefijo}_stats.csv", encoding="utf-8")))
    return {f["Name"]: f for f in filas}


def jpeg_de_5_mb() -> bytes:
    """JPEG con ruido (casi incompresible) de entre 4,7 MB y 5 MB."""
    from PIL import Image

    lado = 1800
    while True:
        datos = io.BytesIO()
        Image.frombytes("RGB", (lado, lado), os.urandom(lado * lado * 3)).save(datos, "JPEG", quality=92)
        tamano = len(datos.getvalue())
        if 4_700_000 <= tamano <= 5 * 1024 * 1024:
            return datos.getvalue()
        lado = int(lado * (4_950_000 / tamano) ** 0.5)


def medir_imagenes(url: str, repeticiones: int = 20) -> list[float]:
    import httpx

    emisor, receptor = httpx.Client(base_url=url, timeout=60), httpx.Client(base_url=url, timeout=60)
    for cliente, n in ((emisor, 9800), (receptor, 9801)):
        cliente.post("/api/sesiones", json={"correo": f"carga{n:05d}@unas.edu.pe", "contrasena": CLAVE}).raise_for_status()
    pid = emisor.post("/api/publicaciones", json={"tipo": "OFREZCO", "titulo": "Fotos", "descripcion": "x"}).json()["id"]
    chat = receptor.post(f"/api/publicaciones/{pid}/respuestas", data={"texto": "hola"}).json()["chat_id"]
    ultimo = receptor.get(f"/api/chats/{chat}").json()["mensajes"][-1]["fecha_envio"]
    tiempos = []
    for _ in range(repeticiones):
        imagen = jpeg_de_5_mb()
        inicio = time.perf_counter()
        r = emisor.post(f"/api/chats/{chat}/mensajes", files={"imagen": ("foto.jpg", imagen, "image/jpeg")})
        r.raise_for_status()
        while True:  # sondeo de 1 s del otro participante, como la página del chat
            nuevos = receptor.get(f"/api/chats/{chat}", params={"despues_de": ultimo},
                                  headers={"X-Actualizacion-Automatica": "1"}).json()["mensajes"]
            if nuevos:
                ultimo = nuevos[-1]["fecha_envio"]
                descarga = receptor.get(nuevos[-1]["imagen_url"])
                descarga.raise_for_status()
                break
            time.sleep(1)
        local = time.perf_counter() - inicio
        red = perfil.segundos_de_transferencia(len(imagen)) + perfil.segundos_de_transferencia(len(descarga.content))
        tiempos.append((local + red) * 1000)
    return tiempos


def medir_registros(url: str, repeticiones: int = 100) -> list[float]:
    import httpx

    cliente, tiempos = httpx.Client(base_url=url, timeout=60), []
    for i in range(repeticiones):
        inicio = time.perf_counter()
        r = cliente.post("/api/cuentas", json={"correo": f"registro{i:03d}@unas.edu.pe", "nickname": f"registro{i:03d}",
                                               "contrasena": CLAVE, "confirmacion": CLAVE, "acepta_terminos": True})
        r.raise_for_status()
        tiempos.append((time.perf_counter() - inicio) * 1000)
    return tiempos


def p95(valores: list[float]) -> float:
    return statistics.quantiles(valores, n=100, method="inclusive")[94]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows usa cp1252
    parser = argparse.ArgumentParser()
    parser.add_argument("--mongo-uri", default=os.environ.get("E2E_MONGO_URI",
                                                              "mongodb://localhost:27017/?replicaSet=rs0&directConnection=true"))
    parser.add_argument("--base", default="la_banca_carga")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--usuarios", type=int, default=perfil.USUARIOS)
    parser.add_argument("--duracion", default=perfil.DURACION)
    parser.add_argument("--salida", default=str(Path(__file__).with_name("resultados")))
    args = parser.parse_args()

    from pymongo import MongoClient

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    registro = salida / "uvicorn.log"
    registro.write_text("")
    cliente = MongoClient(args.mongo_uri)
    cliente.drop_database(args.base)
    db = cliente[args.base]

    app, url = arrancar_app(args.mongo_uri, args.base, args.workers, registro)  # crea colecciones e índices
    try:
        cuentas, activas = sembrar(db)
        print(f"Sembradas {cuentas} cuentas y {activas} publicaciones activas", flush=True)
        inicio = datetime.now(timezone.utc)
        stats = correr_locust(url, args.usuarios, args.duracion, salida / "locust")
        fin = datetime.now(timezone.utc)
        activas_fin = db.publications.count_documents({"status": "ACTIVE", "expiresAt": {"$gt": fin}})
    finally:
        detener(app)

    app, url = arrancar_app(args.mongo_uri, args.base, 1, registro)
    try:
        imagenes = medir_imagenes(url)
        registros = medir_registros(url)
    finally:
        detener(app)

    total = stats["Aggregated"]
    p95_ms = {nombre: float(stats[nombre]["95%"]) for nombre in (perfil.FEED, perfil.FEED_FILTRO, perfil.ENTREGA_TEXTO)}
    p95_ms[perfil.ENTREGA_IMAGEN] = p95(imagenes)
    p95_ms[perfil.CORREO] = p95(registros)
    resultados = perfil.evaluar(int(total["Request Count"]), int(total["Failure Count"]), p95_ms, cuentas,
                                min(activas, activas_fin))
    resumen = {
        "inicio": inicio.isoformat(), "fin": fin.isoformat(), "usuarios": args.usuarios, "duracion": args.duracion,
        "workers": args.workers, "cuentas": cuentas, "publicaciones_activas": [activas, activas_fin],
        "solicitudes": int(total["Request Count"]), "fallos": int(total["Failure Count"]),
        "por_medicion": {n: {"solicitudes": int(f["Request Count"]), "fallos": int(f["Failure Count"]),
                             "p50_ms": float(f["50%"]), "p95_ms": float(f["95%"]), "max_ms": float(f["Max Response Time"])}
                         for n, f in stats.items()},
        "imagenes_ms": imagenes, "registros_p95_ms": p95(registros),
        "resultados": [r.__dict__ for r in resultados],
    }
    (salida / "resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    print("| RNF | Métrica | Valor | Límite | Cumple |\n|---|---|---|---|---|")
    for r in resultados:
        print(f"| {r.rnf} | {r.metrica} | {r.valor} {r.unidad} | {r.limite} {r.unidad} | {'sí' if r.cumple else 'NO'} |")
    return 0 if all(r.cumple for r in resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
