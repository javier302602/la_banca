# La Banca

Red social de la UNAS para estudiantes con correo **@unas.edu.pe**: publicaciones de 24 h, chat, multimedia,
ubicación en vivo, videollamada aleatoria y panel de administradores.

**Stack:** FastAPI (Python 3.14) · MongoDB 7 (replica set) · MinIO/S3 para archivos · plantillas Jinja + JavaScript
sin frameworks · WebSocket (ubicación y videollamada) · WebRTC · Caddy (HTTPS) · Docker Compose.

## Instalar y ejecutar

**Con Docker (recomendado).** Levanta app, MongoDB, MinIO, Caddy, Mailpit y las tareas programadas:

```bash
cp .env.example .env.docker          # una sola vez; cambia las claves marcadas con CAMBIAR
ARCHIVO_ENV=.env.docker docker compose --env-file .env.docker up -d --build
```

En PowerShell: `$env:ARCHIVO_ENV=".env.docker"; docker compose --env-file .env.docker up -d --build`.
Entra a **<https://localhost:8443>** (certificado local: el navegador avisa una vez). Los códigos de activación
llegan a **<http://localhost:8025>** (Mailpit). Apagar: `docker compose --env-file .env.docker down`.
`.env.docker` y `.env` no se suben al repositorio. Guía para un servidor real: [docs/DESPLIEGUE.md](docs/DESPLIEGUE.md).

**Sin Docker (solo para desarrollar).**

```bash
docker run -d --name la-banca-mongo -p 27017:27017 mongo:8.0 --replSet rs0 --bind_ip_all
docker exec la-banca-mongo mongosh --eval 'rs.initiate({_id:"rs0",members:[{_id:0,host:"localhost:27017"}]})'
python -m venv .venv && .venv/Scripts/activate      # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # MONGO_URI=mongodb://localhost:27017/?replicaSet=rs0&directConnection=true, COOKIE_SECURE=false
uvicorn app.main:app --reload --env-file .env       # http://localhost:8000
```

**Pruebas:** `pytest` (unitarias, sin base) · `pytest -m e2e` (MongoDB real) ·
`pytest -m e2e tests/e2e/navegador --timeout=120` (Chromium, Firefox y WebKit; antes:
`python -m playwright install chromium firefox webkit`). Más detalles en [docs/OPERACION.md](docs/OPERACION.md).

## Variables del `.env`

Todas están explicadas en [.env.example](.env.example). Nada sensible va en el código.

| Grupo | Variables | Para qué |
| --- | --- | --- |
| Entorno | `ENTORNO`, `APP_BASE_URL`, `COOKIE_SECURE`, `COMPOSE_PROFILES`, `SITIO`, `PUERTO_HTTP(S)` | desarrollo/producción, dirección pública, HTTPS |
| Base de datos | `MONGO_URI`, `MONGO_DB` | MongoDB (replica set) |
| Archivos | `IMAGE_STORAGE`, `STORAGE_BUCKET`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, `STORAGE_ENDPOINT` | imágenes, video, audios y documentos en MinIO/S3 |
| Correo | `EMAIL_SENDER`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_TLS`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | código de activación, recuperación y avisos de moderación |
| Cuentas | `DOMINIO_INSTITUCIONAL` | solo correos `@unas.edu.pe` |
| Multimedia | `PUBLICACION_VIDEO_MAX_MB`, `AUDIO_MAX_MB` | tamaños máximos |
| Videollamada | `WEBRTC_STUN_URLS`, `WEBRTC_TURN_URL`, `WEBRTC_TURN_USUARIO`, `WEBRTC_TURN_CLAVE` | STUN (Google por omisión) y TURN opcional (coturn) |
| Administración | `ADMIN_EMAILS` | correos de los administradores, separados por comas |
| Tareas | `CRON_SECRET`, `INTERVALO_TAREAS` | limpiezas programadas |
| Reglas | `CFG_MAX_PUBLICACIONES_ACTIVAS`, `CFG_DIAS_RETENCION_REPORTES`, `CFG_HORAS_INACTIVIDAD_SESION`, … | parámetros del sistema |
| Legal | `TERMINOS_VERSION`, `TERMINOS_FECHA`, `CANAL_ARCO` | obligatorios en producción |

Listas editables sin tocar código (se aplican al reiniciar): [config/carreras.json](config/carreras.json) y
[config/palabras_ofensivas.json](config/palabras_ofensivas.json).

## Estructura de carpetas

Vertical Slice Architecture: cada caso de uso tiene su carpeta con `endpoint.py` (ruta) · `request.py` (modelos) ·
`handler.py` (lógica) · `repository.py` (MongoDB).

```text
app/
  features/
    m01_acceso/          registro, código de activación, sesión, recuperar contraseña, nickname
    m02_publicaciones/   crear (imágenes y video), mis publicaciones, cerrar, reacciones (cu21)
    m03_feed/            feed «Ahora» y detalle de publicación
    m04_chat/            responder, enviar mensaje (imagen, audio, documento, sticker), mis chats, ubicación en vivo (cu22)
    m05_reportes/        reportar publicación y chat
    m06_configuracion/   parámetros técnicos
    m07_perfiles/        perfil (foto, avatar, nombre y carrera) y perfil público
    m08_videollamada/    videollamada aleatoria (cu23) y reportar videollamada (cu24)
    m09_admin/           panel (cu25), moderar (cu26), historial (cu27), filtro automático (cu28)
  jobs/                  tareas programadas: limpiar chats y archivos (ea03), reportes (ea05), cuentas sin activar (ea07)
  shared/                base común: config, base de datos, dominio (entidades y contratos), correo, sesión, almacenamiento
web/  templates/ (HTML por módulo) · static/js/ (un archivo por pantalla) · static/css/ (tokens.css + app.css) · i18n/
config/  listas editables · despliegue/  Caddy y gunicorn · scripts/  respaldos, migraciones, datos de demo · tests/
```

## Cómo fluye cada módulo

Todos siguen el mismo camino: **página (HTML + JS) → API (`endpoint.py`) → lógica (`handler.py`) →
`repository.py` → MongoDB** (y MinIO para archivos).

| Módulo | Flujo |
| --- | --- |
| Acceso | registro → valida `@unas.edu.pe` → cuenta PENDIENTE + código de 6 dígitos por correo (10 min, 5 intentos) → `/activar` → ACTIVA → inicio de sesión (cookie). Cuentas suspendidas o baneadas no entran. |
| Publicaciones | publicar (texto, hasta 3 imágenes, 1 video) → `publications` con vencimiento a 24 h → el feed solo muestra las vigentes; las vencidas se ocultan y MongoDB las borra a los 30 días (TTL). Reacciones en `reactions`. |
| Chat | responder una publicación crea el chat → mensajes (texto, imagen, audio, nota de voz, documento, sticker) → la otra persona los recibe cada 1 s con «visto». |
| Ubicación | permiso del navegador → `watchPosition` → WebSocket `/ws/chats/{id}/ubicacion` → `live_locations` (sin historial, vence a los 2 min) → la otra persona la ve. |
| Videollamada | permiso de cámara y micrófono → WebSocket `/ws/videollamada` → cola en `videocall_queue` → emparejamiento al azar → señales por `videocall_signals` → audio y video directo entre navegadores (WebRTC). No se graba. |
| Reportes | botón Reportar (publicación, chat o videollamada) o filtro automático de palabras → `reports` / `videocall_reports` como PENDIENTE → correo a los admins. |
| Administración | `/admin` (solo `ADMIN_EMAILS`) → lista todos los reportes → eliminar contenido, advertir, suspender, banear o descartar → `admin_actions` (historial). |
| Tareas | el servicio `tareas` llama cada hora a `/jobs/*`: borra chats expirados y archivos vencidos, reportes ya revisados y cuentas sin activar. |
