"""Fase 5 — Despliegue portable: docker-compose.yml, Dockerfile, Caddyfile, .env.example y docs/DESPLIEGUE.md.

Pruebas estáticas (sin Docker). El arranque real del compose se prueba en la Fase 7.
"""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
COMPOSE = (RAIZ / "docker-compose.yml").read_text(encoding="utf-8")
DOCKERFILE = (RAIZ / "Dockerfile").read_text(encoding="utf-8")
CADDYFILE = (RAIZ / "despliegue" / "Caddyfile").read_text(encoding="utf-8")
ENV_EJEMPLO = (RAIZ / ".env.example").read_text(encoding="utf-8")
GUIA = (RAIZ / "docs" / "DESPLIEGUE.md").read_text(encoding="utf-8")


def servicio(nombre: str) -> str:
    """Bloque YAML de un servicio (hasta el siguiente servicio de primer nivel)."""
    m = re.search(rf"^  {nombre}:\n(.*?)(?=^  [a-z][\w-]*:\n|^volumes:)", COMPOSE, re.S | re.M)
    assert m, nombre
    return m.group(1)


def variables_env_ejemplo() -> set[str]:
    return set(re.findall(r"^#?\s*([A-Z][A-Z0-9_]*)=", ENV_EJEMPLO, re.M))


def test_servicios_requeridos():
    for nombre in ("mongo", "minio", "minio-init", "app", "tareas", "caddy", "mailpit", "cloudflared"):
        servicio(nombre)


def test_imagenes_fijadas_a_una_version():
    imagenes = re.findall(r"image:\s*(\S+)", COMPOSE)
    for imagen in imagenes:
        valor = re.sub(r"\$\{[A-Z_]+:-([^}]+)\}", r"\1", imagen)  # valor por omisión de ${VAR:-...}
        assert ":" in valor and not valor.endswith(":latest"), imagen
    assert re.search(r"^FROM python:3\.14\.\d+-slim$", DOCKERFILE, re.M)


def test_perfiles_dev_prod_y_tunel():
    assert 'profiles: ["dev"]' in servicio("mailpit")
    assert 'profiles: ["tunel"]' in servicio("cloudflared")
    for siempre in ("mongo", "minio", "app", "caddy", "tareas"):
        assert "profiles:" not in servicio(siempre)
    assert re.search(r"^COMPOSE_PROFILES=dev$", ENV_EJEMPLO, re.M)
    assert "COMPOSE_PROFILES` | `prod`" in GUIA


def test_mongo_replica_set_con_volumen_y_healthcheck():
    mongo = servicio("mongo")
    assert '"--replSet", "rs0"' in mongo and "mongo-datos:/data/db" in mongo
    assert "rs.initiate" in mongo and "healthcheck" in mongo
    assert "ports:" not in mongo  # sin puerto publicado


def test_minio_bucket_privado_y_app_con_s3():
    assert "minio-datos:/data" in servicio("minio")
    assert "127.0.0.1:" in servicio("minio")  # consola solo local
    init = servicio("minio-init")
    assert "mc mb --ignore-existing" in init and "anonymous set none" in init
    app = servicio("app")
    assert "IMAGE_STORAGE: s3" in app and "http://minio:9000" in app
    assert "service_completed_successfully" in app and "service_healthy" in app


def test_app_gunicorn_con_workers_uvicorn_sin_root():
    conf = (RAIZ / "despliegue" / "gunicorn.conf.py").read_text(encoding="utf-8")
    assert 'worker_class = "uvicorn_worker.UvicornWorker"' in conf and "WEB_WORKERS" in conf
    assert "gunicorn" in DOCKERFILE and "USER banca" in DOCKERFILE and "HEALTHCHECK" in DOCKERFILE
    assert "X-Forwarded-Proto" in DOCKERFILE  # el healthcheck no se redirige a HTTPS en producción
    servidor = (RAIZ / "requirements-servidor.txt").read_text(encoding="utf-8")
    assert re.search(r"^gunicorn==\d", servidor, re.M) and re.search(r"^uvicorn-worker==\d", servidor, re.M)


def test_caddy_https_automatico_configurable():
    assert "{$SITIO:localhost}" in CADDYFILE and "reverse_proxy app:8000" in CADDYFILE
    assert "{$ACME_EMAIL}" in CADDYFILE and "https_port {$PUERTO_HTTPS:443}" in CADDYFILE
    caddy = servicio("caddy")
    assert "${PUERTO_HTTPS:-443}" in caddy and "caddy-datos:/data" in caddy


def test_tareas_llama_a_los_jobs_con_cron_secret():
    tareas = servicio("tareas")
    for job in ("ea03-limpiar-chats-expirados", "ea05-depurar-contenido-reportado", "ea07-eliminar-cuentas-no-activadas"):
        assert job in tareas
    assert "Authorization: Bearer $$CRON_SECRET" in tareas
    assert "${CRON_SECRET:?" in tareas  # sin secreto, compose no arranca


def test_env_example_completo():
    """Toda variable que lee el código o el compose está documentada en .env.example."""
    leidas = set()
    for archivo in (RAIZ / "app").rglob("*.py"):
        texto = archivo.read_text(encoding="utf-8")
        leidas |= set(re.findall(r'variable\("([A-Z][A-Z0-9_]*)"', texto))
        leidas |= set(re.findall(r'environ(?:\.get\(|\[)"([A-Z][A-Z0-9_]*)"', texto))
        leidas |= set(re.findall(r'entorno\.get\("([A-Z][A-Z0-9_]*)"', texto))
    leidas |= {v for v in re.findall(r"\$\{([A-Z][A-Z0-9_]*)", COMPOSE)}
    leidas |= set(re.findall(r"\{\$([A-Z][A-Z0-9_]*)", CADDYFILE))
    leidas |= {"WEB_WORKERS", "WEB_TIMEOUT", "NIVEL_LOG"}
    internas = {"CATALOGO_I18N", "VERSION_IMAGEN", "MONGO_URI", "STORAGE_ENDPOINT", "IMAGE_STORAGE",
                "E2E_MONGO_URI", "PUERTO_APP", "FORWARDED_ALLOW_IPS"}
    faltan = leidas - internas - variables_env_ejemplo()
    assert not faltan, faltan
    # MONGO_URI, IMAGE_STORAGE y STORAGE_ENDPOINT se documentan comentadas (las fija el compose)
    for v in ("MONGO_URI", "IMAGE_STORAGE", "STORAGE_ENDPOINT"):
        assert re.search(rf"^# {v}=", ENV_EJEMPLO, re.M), v


def test_env_example_sin_comentarios_en_la_misma_linea():
    """docker compose toma «VAR=   # nota» como valor «# nota»: los comentarios van en su propia línea."""
    for linea in ENV_EJEMPLO.splitlines():
        if re.match(r"^[A-Z][A-Z0-9_]*=", linea):
            assert " #" not in linea, linea


def test_env_example_lista_lo_que_bloquea_produccion():
    for v in ("TERMINOS_VERSION", "TERMINOS_FECHA", "CANAL_ARCO"):
        assert re.search(rf"^{v}=", ENV_EJEMPLO, re.M)
    assert "no arranca" in ENV_EJEMPLO.lower()


@pytest.mark.parametrize("seccion", ["## 1. Requisitos", "## 2. Clonar", "## 3. Configurar `.env`", "## 4. Levantar",
                                     "## 5. Crear el primer usuario", "## 6. Verificar", "Cloudflare Tunnel",
                                     "Tailscale", "docker compose up -d", "scripts.crear_usuario"])
def test_guia_paso_a_paso(seccion):
    assert seccion in GUIA


# --- SMTP_TLS (Mailpit en dev, SMTP real cifrado en prod) ---------------------------------------------------
def test_smtp_tls_modos(monkeypatch):
    import smtplib

    from app.shared.email.sender import SmtpEmailSender

    usados = []

    class Falso:
        def __init__(self, host, puerto, timeout):
            usados.append((type(self).__name__, host, puerto))

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self):
            usados.append("starttls")

        def login(self, *a):
            usados.append("login")

        def send_message(self, m):
            usados.append(m["To"])

    class SMTP(Falso):
        pass

    class SMTP_SSL(Falso):
        pass

    monkeypatch.setattr(smtplib, "SMTP", SMTP)
    monkeypatch.setattr(smtplib, "SMTP_SSL", SMTP_SSL)
    import asyncio

    for modo, esperado in (("starttls", ["SMTP", "starttls"]), ("ssl", ["SMTP_SSL"]), ("ninguno", ["SMTP"])):
        usados.clear()
        asyncio.run(SmtpEmailSender("h", 25, None, None, "a@b.c", modo).enviar_recuperacion("x@unas.edu.pe", "u"))
        assert [u[0] if isinstance(u, tuple) else u for u in usados][:len(esperado)] == esperado
        assert "starttls" in usados if modo == "starttls" else "starttls" not in usados
    with pytest.raises(RuntimeError):
        SmtpEmailSender("h", 25, None, None, "a@b.c", "tls13")


def test_produccion_rechaza_smtp_sin_cifrar():
    from app.shared.config.provider import ConfiguracionInvalida, verificar_entorno

    base = {"ENTORNO": "produccion", "IMAGE_STORAGE": "s3", "EMAIL_SENDER": "smtp", "TERMINOS_VERSION": "2.0",
            "TERMINOS_FECHA": "2026-11-10", "CANAL_ARCO": "arco@unas.edu.pe"}
    verificar_entorno(base)
    with pytest.raises(ConfiguracionInvalida, match="SMTP_TLS=ninguno"):
        verificar_entorno({**base, "SMTP_TLS": "ninguno"})
    with pytest.raises(ConfiguracionInvalida, match="CANAL_ARCO"):
        verificar_entorno({**base, "CANAL_ARCO": ""})


def test_s3_con_endpoint_propio_usa_direcciones_por_ruta(monkeypatch):
    from app.shared.storage.image_storage import S3ImageStorage

    monkeypatch.delenv("STORAGE_ESTILO_DIRECCION", raising=False)
    s3 = S3ImageStorage("la-banca", "http://minio:9000", "k", "s", "us-east-1")
    assert s3._s3.meta.config.s3["addressing_style"] == "path"
    assert S3ImageStorage("b", None, "k", "s", "us-east-1")._s3.meta.config.s3["addressing_style"] == "auto"
