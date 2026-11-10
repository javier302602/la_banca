# Changelog

Todos los cambios relevantes de La Banca se documentan en este archivo.

El formato sigue [Keep a Changelog 1.1.0](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa
[Semantic Versioning 2.0.0](https://semver.org/lang/es/). La versión vigente está en el archivo `VERSION`.

## [Unreleased]

## [2.0.0] - 2026-11-10

Cambio de alcance de SRS v1.9 a v2.0: ver `docs/cambios_v2.md` (solicitud de cambio).

### Added
- Archivo `VERSION`; la versión se muestra en el pie de todas las páginas y en `GET /api/salud`.
- `GET /api/salud`: estado del servicio y de la base de datos para monitores y healthchecks (503 si la base no
  responde).
- **Fase 1 — Rediseño visual:** portada para visitantes con lema y llamada a la acción; paleta con color
  primario (#4f3cc9) y de acento (#c2410c); tarjetas con sombra y bordes redondeados; iconos de Bootstrap Icons
  1.11.3 en el menú, los títulos, las acciones y los tipos de publicación; ilustraciones originales en los estados
  vacíos; tipos de publicación elegidos en mosaicos.
- **Modo claro y oscuro:** interruptor en la barra (`role="switch"`) que respeta `prefers-color-scheme` y recuerda
  la elección en el navegador; todos los colores salen de los tokens, con un juego por modo.
- `tokens.json` con los conjuntos `global`, `claro` y `oscuro`, los temas Claro y Oscuro y sombras `boxShadow`.
- Capturas por página, ancho (360, 768 y 1024 px) y modo (96 en la versión final: 16 páginas × 3 × 2).

- **Fase 2 — Perfiles:** página pública `/perfiles/{nickname}` con foto o avatar, biografía (≤ 160 caracteres)
  y fecha de ingreso; el correo no se muestra a nadie. `/perfil` permite subir una foto (JPG/PNG/WebP ≤ 2 MB,
  recortada a cuadrado de hasta 512 px, re-codificada en WebP y sin EXIF), quitarla, y elegir uno de 12 avatares
  originales agrupados como «Hombre», «Mujer» y «Neutros» solo para presentarlos; sin elección, iniciales sobre un
  color. No se infiere ni se guarda el género. La foto o el avatar aparecen en el feed, el detalle (con enlace al
  perfil), la lista de chats y la cabecera del chat.
- API: `GET/PATCH /api/cuentas/me/perfil`, `PUT/DELETE /api/cuentas/me/foto`, `GET /api/perfiles/{nickname}` y
  `GET /api/perfiles/{nickname}/foto` (con sesión, `nosniff`). Los DTO del feed, el detalle y los chats incluyen
  `apariencia_autor` / `apariencia_contraparte`.
- Tokens `--lb-color-avatar-1…6` (claro y oscuro) para el fondo de las iniciales.
- **Fase 3 — Imágenes en publicaciones:** hasta 3 imágenes JPG/PNG/WebP de hasta 5 MB por publicación,
  validadas por contenido, re-codificadas sin EXIF y comprimidas en el navegador si superan 4 MB; vista previa con
  botón para quitar cada una; miniatura y cantidad en el feed; galería con miniaturas en el detalle.
- Al reportar una publicación, sus imágenes se copian al área de retención (EA-05 las borra al vencer el plazo).
- EA-03 borra además las imágenes de las publicaciones vencidas o cerradas.
- **Fase 4 — Chat estilo Messenger:** burbujas agrupadas por autor con la foto o el avatar de la otra persona
  junto al último mensaje de cada grupo; hora y estado «Enviado» / «Visto» (según su `lastReadAt`); selector de
  32 emojis Unicode (sin librerías) y paquete propio de 20 stickers SVG con nombre accesible; documentos PDF,
  DOCX, XLSX, PPTX y TXT de hasta 10 MB validados por contenido (se rechazan ejecutables, Office con macros y Office
  antiguo), descargados como adjunto con `nosniff` solo por los dos participantes y mostrados como tarjeta con
  icono, nombre y tamaño.
- Los reportes de chat conservan los documentos y los stickers; EA-03 borra los documentos de los chats expirados.
- **Fase 5 — Despliegue portable:** `docker-compose.yml` con la app (gunicorn + workers de uvicorn), MongoDB 7
  como replica set con volumen, MinIO (bucket privado creado al arrancar), Caddy con HTTPS automático, un servicio
  `tareas` que ejecuta EA-03/EA-05/EA-07 y, en el perfil `dev`, Mailpit; perfil `prod` para dominio y SMTP reales
  y perfil opcional `tunel` (Cloudflare Tunnel). `Dockerfile`, `.env.example` completo y comentado,
  `docs/DESPLIEGUE.md` paso a paso (incluye Cloudflare Tunnel y Tailscale), `scripts/crear_usuario.py` y
  `scripts/verificar_despliegue.py`.
- `SMTP_TLS` (`starttls`, `ssl` o `ninguno`; `ninguno` no se permite en producción).
- **Fase 6 — Migración de datos:** `scripts/backup.sh` (mongodump comprimido + copia del bucket de MinIO +
  manifiesto, en un paquete fechado con rotación de 7 días) y `scripts/restore.sh` (reemplaza base y bucket; acepta
  también los volcados de la v1). Migraciones versionadas en `scripts/migraciones/NNN_descripcion.py`, idempotentes,
  aplicadas al arrancar con bloqueo entre procesos y registradas en `schema_migrations`; `scripts/migrar.py`.
  Migración `001_v1_a_v2`. Prueba completa con Docker: respaldo en un contenedor, restauración en otro limpio y
  restauración de un respaldo real de la v1.
- **Fase 7 — Pruebas finales:** `scripts/seed_demo.py` (4 cuentas con avatar, publicaciones con imágenes y chats con
  emojis, stickers y documentos), recorrido completo en el navegador contra el compose levantado desde cero
  (`tests/despliegue/test_recorrido_compose.py`, capturas en `docs/demo/`), 96 capturas de diseño regeneradas
  (16 páginas, incluida la del perfil público) y auditoría de cumplimiento actualizada para la v2.0.0.

### Changed
- Política de privacidad: el estado «visto» y los documentos del chat (publicar una versión nueva de los términos).
- La app aplica las migraciones pendientes al arrancar (también en Vercel: `scripts/migraciones` se incluye).
- `docker-compose.yml`: `ARCHIVO_ENV` permite levantar una segunda instancia con otro archivo de variables.
- `.env.example` reescrito para el despliegue con Docker Compose (valores de dev, notas `[PROD]` en su propia línea).
- S3 con endpoint propio usa direcciones por ruta (`STORAGE_ESTILO_DIRECCION` lo puede forzar).
- El validador `$jsonSchema` de `accounts` incluye `bio` (≤ 160), `avatar` (del catálogo) y `photo`.
- `GET /api/chats/{id}` devuelve `visto_hasta`; los mensajes incluyen `sticker`, `sticker_url` y `documento`.
- El chat expone al otro participante cuándo se leyó su mensaje (la política de privacidad lo informa).
- `POST /api/publicaciones` acepta también `multipart/form-data` (campo `imagenes`); el JSON de v1 sigue
  funcionando igual.
- Términos y política de privacidad: declaran la foto, el avatar, la biografía y la fecha de ingreso como datos
  tratados y que los demás los ven (RN-31). **Hay que subir `TERMINOS_VERSION`** al desplegar.
- `/` sin sesión muestra la portada (antes redirigía al inicio de sesión).
- En tableta (768–1023 px) el menú con sesión muestra solo textos y «Cerrar sesión» como icono, para que quepa.
- axe-core con wcag22aa se ejecuta en modo claro y oscuro.

## [1.0.0] - 2026-11-10

MVP según el SRS v1.9 (136 RF, 50 RN y 38 RNF; ver `docs/auditoria_cumplimiento.md`). Tag `v1.0.0`.

### Added
- **Acceso y cuenta:** registro con correo institucional y activación por enlace, inicio y cierre de sesión con
  sesiones simultáneas, bloqueo tras 5 intentos fallidos (ventana móvil de 15 min), recuperación de contraseña por
  enlace, edición del nickname, términos y política de privacidad versionados.
- **Publicaciones:** tipos Necesito / Ofrezco / Actividad, duración fija de 24 h, máximo de activas configurable,
  cierre manual.
- **Feed «Ahora»:** bloques de 20 con cursor, filtro por tipo, actualización automática, detalle.
- **Chat 1 a 1:** primer mensaje al responder, texto o imagen (JPG/PNG/WebP ≤ 5 MB, sin EXIF), expiración tras
  24 h sin mensajes con aviso previo, indicador de no leídos.
- **Reportes:** de publicaciones y chats, con instantánea conservada 7 días y purga automática.
- **Configuración técnica** por variables de entorno con rangos validados; reloj de pruebas (`ENTORNO=pruebas`).
- **Automatismos:** EA-03, EA-05 y EA-07 por cron y al arrancar; purga de sesiones con retención de 30 días.
- **Interfaz:** mobile-first (360/768/1024), WCAG 2.2 AA verificado con axe-core, catálogo de textos es-PE con
  fechas en America/Lima, ayuda consistente, tokens de diseño exportables a Figma.
- **Operación:** respaldo con `mongodump` y workflow diario cifrado, prueba de carga con Locust, pruebas e2e en
  Chromium, Firefox y WebKit.

[Unreleased]: https://example.invalid/la-banca/compare/v2.0.0...HEAD
[2.0.0]: https://example.invalid/la-banca/compare/v1.0.0...v2.0.0
[1.0.0]: https://example.invalid/la-banca/releases/tag/v1.0.0
