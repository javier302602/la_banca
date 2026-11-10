# Changelog

Todos los cambios relevantes de La Banca se documentan en este archivo.

El formato sigue [Keep a Changelog 1.1.0](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa
[Semantic Versioning 2.0.0](https://semver.org/lang/es/). La versión vigente está en el archivo `VERSION`.

## [Unreleased]

## [2.0.0] - en desarrollo

Cambio de alcance de SRS v1.9 a v2.0: ver `docs/cambios_v2.md` (solicitud de cambio).

### Added
- Archivo `VERSION`; la versión se muestra en el pie de todas las páginas y en `GET /api/salud`.
- `GET /api/salud`: estado del servicio y de la base de datos para monitores y healthchecks (503 si la base no
  responde).

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
