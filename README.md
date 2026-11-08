# La Banca

Monolito modular (FastAPI + MongoDB con la API async de PyMongo + Object Storage) con Vertical Slice Architecture y MVC en la presentación.
Cada caso de uso vive en `app/features/mXX_*/cuXX_*/` (endpoint · request · handler · repository) y cada
automatismo programado en `app/jobs/eaXX_*/`.

## Ejecutar en local

Requisitos: Python 3.14 y un MongoDB **replica set** (las operaciones atómicas usan transacciones).

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

## Configuración técnica (CU-15)

No hay pantalla ni API de administración. Los parámetros se cambian con variables de entorno
(`.env.example`); para revisar los valores efectivos y registrarlos en `system_parameters`:

```bash
python -m app.features.m06_configuracion.cu15_configurar_parametros.endpoint --registrar
```

## Despliegue en Vercel

`vercel.json` reescribe todas las rutas (páginas y `/api/...`) hacia `api/index.py` y programa los crons
de EA-03, EA-05 y EA-07. Define en Vercel las variables de `.env.example`, con `ENTORNO=produccion`, `IMAGE_STORAGE=s3`,
`EMAIL_SENDER=smtp` y un `CRON_SECRET` aleatorio.
