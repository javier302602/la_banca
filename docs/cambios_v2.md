# Solicitud de cambio: SRS v1.9 → v2.0

| Campo | Valor |
|---|---|
| Proyecto | La Banca |
| Versión base | SRS v1.9 · software v1.0.0 (tag `v1.0.0`) |
| Versión propuesta | SRS v2.0 · software v2.0.0 |
| Fecha | 10 de noviembre de 2026 |
| Tipo | Cambio de alcance (funcionalidades nuevas y modificación de requisitos vigentes) |
| Rama | `mejoras-v2` |

## 1. Motivo

La v1.0.0 cumple el SRS v1.9. El grupo propone una v2 con tres objetivos:
1. hacer la aplicación más atractiva y expresiva: identidad visual, perfiles, imágenes y un chat más completo;
2. poder desplegarla en un servidor propio, además de Vercel;
3. garantizar que los datos de la v1 se conservan al actualizar.

Varios cambios contradicen requisitos vigentes del SRS v1.9. Esta solicitud los identifica uno por uno para que se
aprueben de forma explícita y se reflejen en el SRS v2.0.

**Leyenda de tipos:**
- **Nuevo:** requisito que no existía.
- **Modifica:** cambia un requisito vigente.
- **Amplía:** extiende un requisito sin contradecirlo.

## 2. Cambios

### Fase 1 — Rediseño visual

| # | Cambio | Requisitos del SRS v1.9 afectados | Tipo | Justificación |
|---|---|---|---|---|
| 1.1 | Identidad visual con color primario y de acento, tarjetas con sombra y bordes redondeados, iconos (Bootstrap Icons) e ilustraciones en los estados vacíos | RNF-USA-04 (contraste), RNF-USA-02 | Amplía | Hacer la app más atractiva para su público estudiantil sin perder accesibilidad. Los colores siguen en los tokens y se verifican con axe. |
| 1.2 | Portada de inicio para visitantes, con lema y llamada a la acción (antes `/` redirigía al inicio de sesión) | RF-AUT-08 (inicio de sesión muestra el feed): sin cambios. Nueva pantalla pública | Nuevo | Presentar el servicio a quien llega por primera vez. Con sesión, `/` sigue llevando al feed. |
| 1.3 | Modo claro y oscuro con interruptor en la barra; respeta `prefers-color-scheme` y recuerda la elección en el navegador | RNF-USA-04 (debe cumplirse en ambos modos) | Nuevo | Comodidad de lectura y ahorro de batería. La preferencia se guarda solo en el navegador (`localStorage`), no en la cuenta. |

### Fase 2 — Perfiles

| # | Cambio | Requisitos del SRS v1.9 afectados | Tipo | Justificación |
|---|---|---|---|---|
| 2.1 | Página de perfil con nickname, foto o avatar, biografía (máx. 160 caracteres) y fecha de ingreso | **RN-04** («los demás usuarios ven únicamente el nickname») y RNF-PRI-01 | **Modifica** | Dar identidad a quien publica o conversa. RN-04 pasa a decir: «los demás usuarios ven el nickname, la foto o el avatar, la biografía y la fecha de ingreso; **el correo sigue sin mostrarse a nadie**». RNF-PRI-01 no cambia. |
| 2.2 | Foto opcional: JPG/PNG/WebP ≤ 2 MB, recortada a cuadrado, sin EXIF y re-codificada | RN-31 (datos tratados), RNF-PRI-04 | **Modifica** RN-31 · Amplía RNF-PRI-04 | La política de privacidad debe declarar la foto y la biografía como datos tratados: hay que subir `TERMINOS_VERSION`. La foto recibe el mismo saneamiento que las imágenes del chat. |
| 2.3 | Sin foto, la persona **elige** un avatar predefinido (grupos «hombre», «mujer» y «neutro»); si no elige, se muestran sus iniciales sobre un color | Ley N.° 29733 (minimización) | Nuevo | **No se infiere ni se guarda el género**: solo se guarda el identificador del avatar elegido (`avatar-01`…), y la agrupación es solo de presentación. El color de las iniciales se deriva del identificador interno, no de ningún atributo personal. |
| 2.4 | La foto o el avatar aparecen en el feed, el detalle y el chat | RF-FED-04, RF-FED-05, RF-CHT-18, RF-CHT-22 | Amplía | Reconocer de un vistazo a la otra persona. |

### Fase 3 — Imágenes en publicaciones

| # | Cambio | Requisitos del SRS v1.9 afectados | Tipo | Justificación |
|---|---|---|---|---|
| 3.1 | Hasta 3 imágenes por publicación, con las reglas de las del chat (formato, tamaño, sin EXIF, re-codificación), compresión en el navegador y galería en el detalle | RF-PUB-01 («indicando tipo, título y descripción»), RN-08, RF-FED-05 | **Modifica** RF-PUB-01 · Amplía RF-FED-05 | Una foto del objeto que se ofrece o se necesita se entiende mejor que la descripción sola. |
| 3.2 | Al reportar una publicación, sus imágenes se copian a retención como las del chat | RF-REP-06 (copia de tipo, título, descripción y fechas), RN-24 | **Modifica** RF-REP-06 | La evidencia de un reporte debe incluir todo el contenido publicado. |
| 3.3 | Las imágenes de una publicación vencida o cerrada se eliminan del almacenamiento en la siguiente limpieza (EA-03) | RN-11, RNF-PRI-03 (por analogía) | Nuevo | No conservar imágenes personales más allá de la vida de la publicación. Las copias de un reporte siguen el plazo de RN-24. |

### Fase 4 — Chat estilo Messenger

| # | Cambio | Requisitos del SRS v1.9 afectados | Tipo | Justificación |
|---|---|---|---|---|
| 4.1 | Burbujas con la foto o el avatar del otro participante, agrupadas por autor, con hora y estado **enviado / visto** | RF-CHT-11, RF-CHT-21 | **Modifica** RF-CHT-21 | Hasta ahora `lastReadAt` solo marcaba los no leídos para quien lee. Con el cambio, **el otro participante sabe si se leyó su mensaje**: la política de privacidad debe informarlo. |
| 4.2 | Selector de emojis (Unicode, sin librerías) y paquete de 20 stickers SVG originales del proyecto (sin personajes ni marcas de terceros) | **RN-19** («texto o una sola imagen»), RF-CHT-08 | **Modifica** RN-19 | Un mensaje pasa a ser **texto, imagen, sticker o documento** (exactamente uno). Los emojis son texto Unicode y cuentan para el límite de 500 caracteres. |
| 4.3 | Documentos adjuntos: PDF, DOCX, XLSX, PPTX y TXT de hasta 10 MB. Tipo validado por contenido; se rechazan ejecutables y Office con macros (`.docm`, `.xlsm`, `.pptm`). Se sirven solo a los dos participantes con `Content-Disposition: attachment` y `X-Content-Type-Options: nosniff`, y se muestran como tarjeta con icono, nombre y tamaño | **RN-19** y **RF-CHT-10** («no debe permitir … archivos que no sean imágenes»), RNF-SEG-04, RNF-REN-04 | **Modifica** | Compartir apuntes y prácticas es un caso de uso frecuente. Controles: validación por contenido y descarga forzada para impedir la ejecución en el navegador. |
| 4.4 | Los reportes de chat conservan también los documentos | RF-REP-17, RN-24 | Amplía | Evidencia completa del chat reportado. |

### Fase 5 — Despliegue en un servidor propio

| # | Cambio | Requisitos del SRS v1.9 afectados | Tipo | Justificación |
|---|---|---|---|---|
| 5.1 | `docker-compose.yml` con app (gunicorn + workers uvicorn), MongoDB 7 replica set con volumen, MinIO, Mailpit y Caddy con HTTPS automático; perfiles `dev` y `prod`; todo configurable por variables | RNF-SEG-03 (TLS), RNF-DIS-01, RNF-MAN-01 | Amplía | Desplegar sin depender de Vercel ni de servicios gestionados. Caddy termina TLS y la app mantiene la redirección a HTTPS y HSTS. |
| 5.2 | Se mantiene el bloqueo del arranque en producción sin términos, `CANAL_ARCO` ni proveedores reales | RN-31, RNF-LEG-01/03 | Sin cambio | — |
| 5.3 | Acceso sin abrir puertos mediante Cloudflare Tunnel o Tailscale (documentado) | RNF-SEG-03 | Nuevo (opcional) | Útil cuando el servidor está detrás de un router doméstico. |
| 5.4 | Automatismos (EA-03, EA-05, EA-07) con un servicio de tareas dentro del compose | RNF-PRI-02, RNF-PRI-03 | Amplía | Sin Vercel Cron ni GitHub Actions, el despliegue propio necesita su propio planificador. |

### Fase 6 — Migración de datos

| # | Cambio | Requisitos del SRS v1.9 afectados | Tipo | Justificación |
|---|---|---|---|---|
| 6.1 | `scripts/backup.sh` y `scripts/restore.sh`: base de datos y archivos de MinIO en un paquete fechado, con rotación de 7 días | RNF-PRI-02 (copias ≤ 7 días), PA-37 | Amplía | Respaldo completo: base y archivos. |
| 6.2 | Migraciones de esquema versionadas, idempotentes y registradas, que se aplican al arrancar. La 001 convierte datos de v1 a v2 | RNF-MAN-01 | Nuevo | Actualizar sin pasos manuales y poder restaurar un respaldo de la v1 sobre la v2. |

### Fase 7 — Pruebas finales y datos de demostración

| # | Cambio | Requisitos del SRS v1.9 afectados | Tipo | Justificación |
|---|---|---|---|---|
| 7.1 | `scripts/seed_demo.py` (4 usuarios con avatar, publicaciones con imágenes y chats con emojis, stickers y documentos) y recorrido del flujo completo sobre el compose | — | Nuevo | Demostración y verificación integral. |

## 3. Impacto

- **Privacidad:** la política de privacidad debe incluir la foto, la biografía, los documentos adjuntos y el estado
  «visto». Hay que subir `TERMINOS_VERSION` antes de publicar la v2.
- **Datos:** campos nuevos en `accounts` (bio, avatar, foto), `publications` (imágenes) y `messages` (sticker,
  documento). La migración 001 los inicializa en los datos de la v1.
- **Almacenamiento:** las fotos, las imágenes de publicaciones y los documentos aumentan el uso del almacenamiento de
  objetos. El dimensionamiento del Entregable 2 §7.4 debe revisarse.
- **Pruebas:** axe con wcag22aa en modo claro y oscuro, e2e en tres motores y prueba de respaldo y restauración
  entre contenedores.

## 4. Aprobación

| Rol | Nombre | Fecha | Decisión |
|---|---|---|---|
| Responsable del producto | | | |
| Responsable técnico | | | |
