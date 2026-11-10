# Despliegue de La Banca con Docker Compose

Esta guía es para quien no conoce el proyecto. Al terminar tendrás La Banca funcionando en tu computadora (perfil
**dev**) o en un servidor con dominio propio (perfil **prod**).

## Qué se levanta

| Servicio | Para qué sirve | ¿Expuesto? |
|---|---|---|
| `caddy` | Proxy con **HTTPS automático** (Let's Encrypt con un dominio real; certificado local con `localhost`) | Sí: `PUERTO_HTTP` y `PUERTO_HTTPS` |
| `app` | La aplicación (FastAPI con gunicorn y workers de uvicorn) | No, solo detrás de Caddy |
| `mongo` | MongoDB 7 como *replica set* (`rs0`), con sus datos en el volumen `mongo-datos` | No |
| `minio` + `minio-init` | Almacenamiento de imágenes, fotos y documentos (bucket privado, volumen `minio-datos`) | Consola solo en `127.0.0.1:9001` |
| `tareas` | Ejecuta cada hora los automatismos EA-03, EA-05 y EA-07 | No |
| `mailpit` | **Solo dev**: recibe todos los correos y los muestra en una web | `127.0.0.1:8025` |
| `cloudflared` | **Opcional**: publica la app sin abrir puertos (Cloudflare Tunnel) | No |

Todo se configura en el archivo `.env`; nada está fijo en el código.

## 1. Requisitos

- **Docker** con **Docker Compose v2.24 o superior** (`docker compose version`). En Windows y macOS, Docker
  Desktop; en Linux, Docker Engine y el plugin `docker-compose-plugin`.
- **Git** para clonar el repositorio.
- 2 GB de RAM libres y 5 GB de disco (más lo que ocupen las imágenes y los documentos que suban).
- Para **prod**: un servidor con IP pública, un **dominio** cuyo registro DNS `A`/`AAAA` apunte a él, los puertos
  **80 y 443** abiertos (o un túnel, ver el punto 8) y una cuenta **SMTP** real para enviar correos.

## 2. Clonar

```bash
git clone <url-del-repositorio> la_banca
cd la_banca
```

## 3. Configurar `.env`

```bash
cp .env.example .env
```

Abre `.env` con un editor. Cada variable está comentada.

### Perfil dev (tu computadora)

Los valores de ejemplo ya sirven. Solo **cambia las claves** marcadas con `CAMBIAR`:

- `STORAGE_ACCESS_KEY` y `STORAGE_SECRET_KEY`: usuario y clave del almacenamiento (solo letras y dígitos; la
  clave de 8 caracteres o más).
- `CRON_SECRET`: un secreto largo. Puedes generarlo con
  `python -c "import secrets; print(secrets.token_urlsafe(32))"`.

La app quedará en **https://localhost:8443** (el navegador avisará del certificado local la primera vez: acéptalo)
y los correos en **http://localhost:8025**.

### Perfil prod (servidor con dominio)

Además de las claves, cambia lo marcado con `[PROD]`:

| Variable | Valor en producción |
|---|---|
| `COMPOSE_PROFILES` | `prod` |
| `ENTORNO` | `produccion` (redirige a HTTPS, envía HSTS y **no arranca** si falta algo obligatorio) |
| `SITIO` | tu dominio, p. ej. `banca.unas.edu.pe` |
| `PUERTO_HTTP` / `PUERTO_HTTPS` | `80` / `443` |
| `ACME_EMAIL` | correo para los avisos de Let's Encrypt |
| `APP_BASE_URL` | `https://banca.unas.edu.pe` (va en los enlaces de los correos) |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_TLS`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | los de tu servidor de correo; `SMTP_TLS` debe ser `starttls` (587) o `ssl` (465) |
| `TERMINOS_VERSION`, `TERMINOS_FECHA` | versión y fecha de la política de privacidad publicada |
| `CANAL_ARCO` | correo o URL oficial para ejercer los derechos ARCO (Ley N.° 29733) |
| `DOMINIO_INSTITUCIONAL` | dominio de los correos de los estudiantes |

Con `ENTORNO=produccion` la app se niega a arrancar si faltan `TERMINOS_VERSION`, `TERMINOS_FECHA` o
`CANAL_ARCO`, si el correo no es SMTP cifrado o si el almacenamiento no es S3. El motivo aparece en
`docker compose logs app`.

> **No subas `.env` al repositorio**: contiene claves. Ya está en `.gitignore`.

## 4. Levantar

```bash
docker compose up -d
```

La primera vez descarga las imágenes y construye la de la app (unos minutos). Comprueba que todo esté en marcha:

```bash
docker compose ps
```

`mongo`, `minio`, `app` deben estar `healthy`; `minio-init` termina (`exited (0)`) tras crear el bucket.

Las migraciones de datos se aplican solas al arrancar la app (ver la sección 9).

## 5. Crear el primer usuario

El registro normal (`/registro`) envía un enlace de activación por correo. Para crear una cuenta ya activada sin
depender del correo (por ejemplo, la primera):

```bash
docker compose exec app python -m scripts.crear_usuario --correo nombre.apellido@unas.edu.pe --nickname mi_nick
```

Pide la contraseña por teclado (8 a 64 caracteres). El correo debe ser del `DOMINIO_INSTITUCIONAL`.

## 6. Verificar

1. Abre la URL (`https://localhost:8443` en dev o `https://tu-dominio` en prod): se ve la portada y, en el pie,
   la versión.
2. `https://<url>/api/salud` responde `{"estado": "ok", "version": "...", "base_de_datos": "ok"}`.
3. Inicia sesión con el usuario del paso 5, publica algo con una imagen y abre el detalle.
4. En dev, regístrate con otra cuenta y busca el correo de activación en `http://localhost:8025`.

O, con Python en tu computadora (`pip install -r requirements-dev.txt`), el recorrido automático:

```bash
python scripts/verificar_despliegue.py --url https://localhost:8443 --mailpit http://localhost:8025 --inseguro
```

(registra una cuenta, la activa con el correo de Mailpit, sube una foto de perfil, publica con imagen y la cierra.
En prod usa solo `--url https://tu-dominio`: comprueba la salud, la versión y HSTS.)

## 7. Operación diaria

| Tarea | Comando |
|---|---|
| Ver registros | `docker compose logs -f app` (o `caddy`, `tareas`, `mongo`) |
| Detener | `docker compose stop` |
| Volver a levantar | `docker compose up -d` |
| Actualizar a una versión nueva | `git pull && docker compose up -d --build` |
| Respaldar / restaurar | `scripts/backup.sh` y `scripts/restore.sh` (sección 9) |
| Borrarlo **todo**, datos incluidos | `docker compose down -v` (¡irreversible!) |

Los datos viven en los volúmenes `mongo-datos` y `minio-datos`: sobreviven a `down`, `up --build` y a
reinicios del servidor (los servicios se reinician solos: `restart: unless-stopped`).

## 8. Acceso sin abrir puertos

Si el servidor está detrás de un router o en una red que no permite abrir los puertos 80/443:

### Opción A: Cloudflare Tunnel (público, con tu dominio en Cloudflare)

1. En Cloudflare Zero Trust → **Networks → Tunnels → Create a tunnel** (tipo *Cloudflared*). Copia el **token**.
2. En el túnel, agrega un **Public hostname**: `banca.tu-dominio` → servicio `http://app:8000`.
   (Cloudflare termina el HTTPS y envía `X-Forwarded-Proto: https`, así que Caddy no es necesario.)
3. En `.env`: `CLOUDFLARE_TUNNEL_TOKEN=<token>`, `COMPOSE_PROFILES=prod,tunel`,
   `APP_BASE_URL=https://banca.tu-dominio`. Deja `PUERTO_HTTP`/`PUERTO_HTTPS` en puertos libres (p. ej. 8080/8443):
   Caddy seguirá sirviendo en local.
4. `docker compose up -d`. El servicio `cloudflared` mantiene el túnel abierto.

### Opción B: Tailscale (acceso privado para los dispositivos de tu red Tailscale)

Nadie fuera de tu *tailnet* puede entrar y no se abre ningún puerto en el router.

1. En el servidor (Linux): instala Tailscale (`curl -fsSL https://tailscale.com/install.sh | sh`), ejecuta
   `sudo tailscale up` y, en la consola de Tailscale, activa **MagicDNS** y **HTTPS Certificates**.
2. Averigua el nombre del servidor con `tailscale status` (p. ej. `servidor.tu-tailnet.ts.net`).
3. En `.env`: `SITIO=servidor.tu-tailnet.ts.net`, `APP_BASE_URL=https://servidor.tu-tailnet.ts.net`,
   `PUERTO_HTTP=80`, `PUERTO_HTTPS=443`.
4. En `docker-compose.yml`, descomenta en el servicio `caddy` la línea del socket de Tailscale
   (`/var/run/tailscale/tailscaled.sock`): Caddy obtiene así el certificado de `*.ts.net` directamente de
   Tailscale, sin Let's Encrypt.
5. `docker compose up -d` y entra desde cualquier dispositivo de la tailnet a `https://servidor.tu-tailnet.ts.net`.

Para acceso público sin abrir puertos usa la opción A (o `tailscale funnel`, que publica el servicio en Internet).

## 9. Respaldos y migraciones

### Respaldar

```bash
scripts/backup.sh
```

Crea **un** paquete fechado `respaldos/la-banca-AAAAMMDD-HHMMSSZ.tar.gz` con:

- `mongo.archive.gz`: volcado comprimido de la base (`mongodump --archive --gzip`);
- `archivos/`: copia del bucket de MinIO (imágenes, fotos de perfil y documentos);
- `MANIFIESTO.txt`: versión de la app, fecha, base, bucket, documentos por colección y número de archivos.

Borra los paquetes de más de 7 días (`RETENCION_RESPALDOS_DIAS`, máximo 7: el contenido reportado no puede
sobrevivir en las copias más de ese plazo). Programa uno diario con cron, p. ej.
`0 3 * * * cd /ruta/la_banca && scripts/backup.sh >> respaldos/registro.txt 2>&1`, y copia la carpeta
`respaldos/` **fuera del servidor**: contiene datos personales, guárdala cifrada.

### Restaurar (en el mismo servidor o en uno nuevo)

```bash
docker compose up -d                                   # en un servidor nuevo: pasos 1 a 4 de esta guía
scripts/restore.sh respaldos/la-banca-AAAAMMDD-HHMMSSZ.tar.gz
```

Pide confirmar (o usa `--si`), detiene la app, **reemplaza** la base completa y el bucket por los del paquete y
vuelve a levantar la app, que aplica las migraciones pendientes.

**Respaldo de la versión 1.** También acepta los volcados de la v1 (`la_banca_db-AAAAMMDDTHHMMSSZ.archive.gz`,
de `scripts/respaldo_mongodb.py` o del workflow de GitHub; si está cifrado, primero
`gpg --decrypt archivo.archive.gz.gpg > archivo.archive.gz`). Esos volcados solo traen la base: las imágenes de
chat de la v1 siguen en el almacenamiento que usaba entonces. Al arrancar, la migración 001 agrega a esos datos
los campos de la v2 (perfil, imágenes de publicación, adjuntos).

### Migraciones

Los cambios de esquema están en `scripts/migraciones/NNN_descripcion.py` (numeradas, idempotentes). La app
aplica las pendientes al arrancar, en orden, y las registra en la colección `schema_migrations`; si arrancan
varios procesos a la vez, solo uno migra. Para ver su estado o aplicarlas a mano:

```bash
docker compose exec app python -m scripts.migrar --estado
docker compose exec app python -m scripts.migrar
```

## 10. Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `app` no llega a `healthy` | `docker compose logs app`. Con `ENTORNO=produccion`, falta una variable obligatoria (el mensaje la nombra). |
| `required variable ... is missing` al hacer `up` | Falta `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY` o `CRON_SECRET` en `.env`. |
| `bind: address already in use` | Otro programa usa el puerto: cambia `PUERTO_HTTP`, `PUERTO_HTTPS`, `PUERTO_MAILPIT` o `PUERTO_CONSOLA_MINIO`. |
| El navegador no confía en `https://localhost:8443` | Es el certificado local de Caddy en dev: acéptalo. En prod, con un dominio real, el certificado es de Let's Encrypt. |
| No llega el correo de activación (prod) | Revisa `SMTP_*` y `docker compose logs app`; prueba el usuario y la clave con tu proveedor. |
| Let's Encrypt no emite el certificado | El DNS del dominio no apunta al servidor o los puertos 80/443 no están abiertos (`docker compose logs caddy`). |

## Notas de seguridad

- MongoDB y MinIO solo son accesibles dentro de la red interna de Compose. MongoDB corre sin autenticación porque
  no se publica ningún puerto; si lo expones, actívala.
- La imagen de MinIO por defecto es una compilación comunitaria (`pgsty/minio`) del código AGPLv3 de MinIO,
  porque la imagen oficial dejó de publicarse en Docker Hub. Puedes usar otra con `MINIO_IMAGEN`.
- Las imágenes de contenedor están fijadas a versiones concretas en `docker-compose.yml`.
