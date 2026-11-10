"""Configuración de gunicorn para el contenedor de la app. Todo sale de variables de entorno."""
import os

bind = f"0.0.0.0:{os.environ.get('PUERTO_APP', '8000')}"
workers = int(os.environ.get("WEB_WORKERS", "2"))
worker_class = "uvicorn_worker.UvicornWorker"
timeout = int(os.environ.get("WEB_TIMEOUT", "60"))
graceful_timeout = 20
keepalive = 5
# El proxy (Caddy) está en la red interna de Docker: se confía en sus cabeceras X-Forwarded-*
forwarded_allow_ips = os.environ.get("FORWARDED_ALLOW_IPS", "*")
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("NIVEL_LOG", "info")
