# La Banca — imagen de la app (FastAPI + gunicorn con workers de uvicorn)
FROM python:3.14.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt requirements-servidor.txt ./
RUN pip install -r requirements-servidor.txt

COPY VERSION ./
COPY app ./app
COPY web ./web
COPY scripts ./scripts
COPY despliegue/gunicorn.conf.py ./despliegue/gunicorn.conf.py

# Sin privilegios de root
RUN useradd --system --uid 10001 --no-create-home banca
USER banca

EXPOSE 8000
# /api/salud responde 503 si la base no está disponible. X-Forwarded-Proto evita la redirección a HTTPS en producción.
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request as u; u.urlopen(u.Request('http://127.0.0.1:8000/api/salud', headers={'X-Forwarded-Proto': 'https'}), timeout=4)"

CMD ["gunicorn", "--config", "despliegue/gunicorn.conf.py", "app.main:app"]
