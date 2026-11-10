# La Banca

Monolito modular (FastAPI + MongoDB con la API async de PyMongo + Object Storage) con Vertical Slice Architecture y MVC en la presentación.
Cada caso de uso vive en `app/features/mXX_*/cuXX_*/` (endpoint · request · handler · repository) y cada
automatismo programado en `app/jobs/eaXX_*/`.

## Ejecutar en local

Requisitos: Python 3.14 (fijado en `.python-version`; Vercel soporta 3.12, 3.13 y 3.14) y un MongoDB **replica set** (las operaciones atómicas usan transacciones).

```bash
# 1. MongoDB local como replica set (Docker)
docker run -d --name la-banca-mongo -p 27017:27017 mongo:8.0 --replSet rs0 --bind_ip_all
docker exec la-banca-mongo mongosh --eval 'rs.initiate({_id:"rs0",members:[{_id:0,host:"localhost:27017"}]})'

# 2. Entorno de Python
python -m venv .venv
.venv/Scripts/activate            # Windows (en Linux/macOS: source .venv/bin/activate)
pip install -r requirements-dev.txt

# 3. Configuración
cp .env.example .env              # y ajusta los valores; para http://localhost usa COOKIE_SECURE=false
#   MONGO_URI=mongodb://localhost:27017/?replicaSet=rs0&directConnection=true

# 4. Servidor (carga .env)
uvicorn app.main:app --reload --env-file .env
```

Abre <http://localhost:8000>. Con `EMAIL_SENDER=consola` los enlaces de activación y recuperación se
escriben en el registro del servidor (`[correo de desarrollo] ... -> http://localhost:8000/activar?token=...`).
Con `IMAGE_STORAGE=memoria` las imágenes viven en la memoria del proceso (se pierden al reiniciar).

## Pruebas

```bash
pytest
```

Los tests de handlers usan fakes en memoria de los contratos y un reloj falso (`tests/fakes.py`); no
necesitan MongoDB.

Las pruebas de punta a punta (`tests/e2e/`) se excluyen por defecto y usan un MongoDB real (replica set,
como el del paso 1; otra URI con `E2E_MONGO_URI`). Vacían la base `la_banca_e2e`:

```bash
pytest -m e2e
```

`tests/e2e/navegador/` abre la app en navegadores reales con Playwright (formularios, 360 px, axe-core, teclado
y flujos principales). Corren en Chromium, Firefox y WebKit (RNF-COM-01), y en Chromium y WebKit también con
emulación de Pixel 7 e iPhone 14. Instala los navegadores una vez:

```bash
pip install -r requirements-dev.txt
python -m playwright install chromium firefox webkit
NAVEGADORES=chromium pytest -m e2e tests/e2e/navegador   # opcional: limitar los motores
```

## Configuración técnica (CU-15)

No hay pantalla ni API de administración. Los parámetros se cambian con variables de entorno
(`.env.example`); para revisar los valores efectivos y registrarlos en `system_parameters`:

```bash
python -m app.features.m06_configuracion.cu15_configurar_parametros.endpoint --registrar
```

## Entorno de pruebas con reloj controlable (RNF-MAN-02)

Con `ENTORNO=pruebas` la app usa un reloj que se puede adelantar para comprobar los plazos de 24 h y 72 h sin
esperarlos. Úsalo con **un solo worker**: el desfase vive en la memoria del proceso.

```bash
curl -X POST -H "Authorization: Bearer $CRON_SECRET" -H "Content-Type: application/json" \
     -d '{"horas": 24}' http://localhost:8000/pruebas/reloj/avanzar     # también: GET /pruebas/reloj, POST /pruebas/reloj/reiniciar
```

En cualquier otro entorno esas rutas responden 404.

## Diseño: tokens, capturas e investigación

- `web/static/css/tokens.css` es la fuente de colores, tipografía, espaciado y puntos de quiebre (360/768/1024).
  `python scripts/exportar_tokens.py` genera `docs/investigacion/tokens.json` para Tokens Studio (Figma).
- `python scripts/tomar_capturas.py --mongo-uri "<replica set>"` captura las 15 páginas en los tres anchos.
- `docs/investigacion/`: evaluación heurística y Gestalt (01), WCAG 2.2 e i18n (02) y diseño responsivo (03).
- Textos de la interfaz: `web/i18n/es-PE.json` (único idioma activo).

## Respaldos (Entregable 2 §8.1)

`scripts/respaldo_mongodb.py` ejecuta `mongodump --gzip --archive` y elimina los respaldos de más de 7 días
(PA-37, RNF-PRI-02; la retención no puede superar 7 días). Requiere MongoDB Database Tools en el PATH:

```bash
MONGO_URI="mongodb+srv://..." python scripts/respaldo_mongodb.py --destino /ruta/respaldos
```

`.github/workflows/backup.yml` lo ejecuta a diario (03:00 UTC−5) y sube el volcado **cifrado** (GPG, AES-256) como
artifact con retención de 7 días. Se activa al crear estos secrets del repositorio:

- `MONGO_URI`: cadena de conexión de producción. Sin ella, el workflow termina sin hacer nada.
- `BACKUP_PASSPHRASE`: frase de cifrado. Es obligatoria, porque el volcado contiene datos personales y los artifacts
  los descarga cualquiera con acceso de lectura al repositorio. Guárdala fuera de GitHub: sin ella no se puede
  restaurar.

Para restaurar: `gpg --decrypt <archivo>.gpg > dump.archive.gz` y `mongorestore --gzip --archive=dump.archive.gz --uri ...`.

## Despliegue en Vercel

`vercel.json` reescribe todas las rutas (páginas y `/api/...`) hacia `api/index.py` y programa los crons
de EA-03, EA-05 y EA-07. Define en Vercel las variables de `.env.example`, con `ENTORNO=produccion`, `IMAGE_STORAGE=s3`,
`EMAIL_SENDER=smtp` y un `CRON_SECRET` aleatorio.

La política de privacidad necesita además tres datos del texto legal aprobado. Con `ENTORNO=produccion`
la app **no arranca** si falta alguno (RN-31, RNF-LEG-01–03):

| Variable | Contenido | Ejemplo |
|---|---|---|
| `TERMINOS_VERSION` | Versión del texto aprobado; se muestra en la política y se registra en cada aceptación (RF-AUT-17) | `1.0` |
| `TERMINOS_FECHA` | Fecha de esa versión | `2026-11-01` |
| `CANAL_ARCO` | Canal oficial para ejercer los derechos ARCO (Ley N.° 29733); reemplaza `{{CANAL_ARCO}}` en `web/terminos/terminos.txt` | `datospersonales@unas.edu.pe` |

Al cambiar el texto de `web/terminos/terminos.txt`, sube `TERMINOS_VERSION` y `TERMINOS_FECHA`.
