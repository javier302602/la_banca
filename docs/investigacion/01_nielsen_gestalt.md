# Evaluación heurística (Nielsen) y leyes de Gestalt — La Banca

**Fecha:** 10 de noviembre de 2026 · **Rama:** `temas-investigacion` · **Alcance:** las 15 páginas de la aplicación.

## 1. Método

- **Heurísticas:** las 10 de Nielsen (1994). H1 visibilidad del estado del sistema; H2 coincidencia con el mundo real; H3 control y libertad del usuario; H4 consistencia y estándares; H5 prevención de errores; H6 reconocer antes que recordar; H7 flexibilidad y eficiencia; H8 diseño estético y minimalista; H9 ayudar a reconocer, diagnosticar y recuperarse de errores; H10 ayuda y documentación.
- **Escala de severidad de Nielsen:**
  - **0:** no es un problema de usabilidad.
  - **1:** solo cosmético.
  - **2:** problema menor (baja prioridad).
  - **3:** problema mayor (alta prioridad, hay que corregirlo).
  - **4:** catástrofe (debe corregirse antes del lanzamiento).
- **Evidencia:** recorrido de cada página a 360 px y a 1024 px, con datos de ejemplo sembrados por `scripts/tomar_capturas.py` (tres cuentas, publicaciones de los tres tipos y un chat con mensajes), y revisión del código de las plantillas y del JS.
- **Limitación:** es una evaluación de **un solo evaluador**. Nielsen recomienda 3 a 5 evaluadores independientes, porque cada uno encuentra en torno a un tercio de los problemas. Conviene que el grupo la repita y consolide las severidades.

**Páginas evaluadas (15):** Iniciar sesión, Registro, Activar cuenta, Recuperar contraseña, Restablecer contraseña, Términos y privacidad, Feed «Ahora», Detalle de publicación, Crear publicación, Mis publicaciones, Mis chats, Chat, Responder, Reportar (publicación y chat comparten pantalla) y Perfil.

## 2. Hallazgos

| # | Página | Heurística | Problema | Sev. | Corrección |
|---|---|---|---|---|---|
| 1 | Todas (menú) | H1 Visibilidad | Nada avisa de mensajes nuevos fuera de «Mis chats». Como un chat expira a las 24 h sin mensajes (RN-20), un mensaje inadvertido puede hacer perder la conversación. | **3** | **Corregido.** El menú muestra «N nuevo(s)» junto a «Mis chats»; se actualiza cada 30 s con un sondeo automático que no reinicia la sesión (RF-AUT-25). |
| 2 | Crear publicación | H5 Prevención de errores | Con 3 publicaciones activas el formulario se completa entero y el error llega al enviar. | **3** | **Corregido.** Aviso previo con enlace a «Mis publicaciones» y botón Publicar deshabilitado. El servidor sigue validando (RF-PUB-06). |
| 3 | Responder | H6 Reconocer antes que recordar | No se muestra la publicación a la que se responde: hay que recordar el título y el autor. | **3** | **Corregido.** Tarjeta con tipo, título, descripción y autor sobre el formulario. |
| 4 | Responder | H5 Prevención de errores | Si la publicación ya no está disponible, el error solo aparecía al enviar. | 2 | **Corregido** con el #3: se informa al cargar y se deshabilita el formulario. |
| 5 | Feed | H4 Consistencia / H8 | Las etiquetas de los tres tipos tenían el mismo gris: el tipo no se distinguía de un vistazo. | 2 | **Corregido** (Gestalt, similitud): color propio por tipo en la etiqueta y en el borde de la tarjeta, también en el detalle, en «Mis publicaciones» y al responder. |
| 6 | Mis chats | H8 Diseño estético | A 360 px la hora del último mensaje se montaba sobre el título de la publicación. | 2 | **Corregido** (Gestalt, proximidad): rejilla de dos columnas. |
| 7 | Chat | H4 / H8 | Los mensajes seguidos del mismo autor tenían la misma separación que un cambio de autor. | 2 | **Corregido** (Gestalt, proximidad): los consecutivos se agrupan. |
| 8 | Chat, Responder | H2 Coincidencia con el mundo real | El selector de archivo nativo usa los textos del navegador («Choose File / No file chosen» en un navegador en inglés). | 2 | Se trata en el tema 2 (i18n). |
| 9 | Crear publicación | H5 / H7 | Los radios de tipo miden 16 px y son difíciles de pulsar en móvil. | 2 | Se trata en el tema 2 (WCAG 2.5.8). |
| 10 | Todas | H10 Ayuda y documentación | No hay ayuda: nada explica los plazos de 24 h, la activación ni qué pasa al reportar. | 2 | Se trata en el tema 2 (WCAG 3.2.6, ayuda consistente). |
| 11 | Todas (menú) | H1 Visibilidad | El menú no marca la sección actual. | 2 | Pendiente. |
| 12 | Iniciar sesión | H7 Flexibilidad | Tras un cierre por inactividad se vuelve al feed y no a la página donde se estaba. | 2 | Pendiente. **Choca con el SRS:** RF-AUT-08 exige mostrar el feed al iniciar sesión. |
| 13 | Registro | H5 Prevención de errores | No se puede mostrar la contraseña al escribirla; en móvil los errores de tipeo son frecuentes. | 2 | Pendiente. |
| 14 | Registro | H1 Visibilidad | Tras registrarse no se dice que el enlace vence en 24 h ni que se puede pedir otro. | 2 | Pendiente. |
| 15 | Detalle | H7 Flexibilidad | Una publicación propia no se puede cerrar desde su detalle; hay que ir a «Mis publicaciones». | 2 | Pendiente. |
| 16 | Mis publicaciones | H3 Control y libertad / H4 | El cierre usa el `confirm()` nativo: aspecto ajeno al resto y sin el título de la publicación. | 2 | Pendiente. |
| 17 | Mis chats, Chat | H1 Visibilidad | No se ve cuánto falta para que el chat expire hasta los últimos 10 min (el aviso que fija RN-21). | 2 | Pendiente. Mostrar el plazo antes es compatible con el SRS. |
| 18 | Chat | H1 Visibilidad | Si llega un mensaje mientras se lee más arriba, no hay aviso de «mensajes nuevos». | 2 | Pendiente. |
| 19 | Reportar | H6 Reconocer antes que recordar | No se muestra qué publicación o chat se reporta. | 2 | Pendiente. |
| 20 | Iniciar sesión | H9 Recuperación de errores | Tras 4 fallos no se advierte que el siguiente bloqueará el correo 15 min. | 1 | Pendiente. El mensaje uniforme lo fija RF-AUT-09. |
| 21 | Recuperar contraseña | H2 | El mensaje «Si el correo tiene una cuenta activada…» puede resultar ambiguo. | 1 | Sin cambio: la ambigüedad es intencional (RN-47, no revelar cuentas). |
| 22 | Activar cuenta | H1 | «Activando tu cuenta…» no tiene indicador de progreso. | 1 | Pendiente (la activación tarda menos de 1 s). |
| 23 | Términos | H8 | Texto largo en un solo bloque, sin índice de secciones. | 1 | Pendiente. |
| 24 | Feed | H1 | Una publicación que vence sigue en la lista («Expirada») hasta la siguiente actualización, y su detalle responde «no disponible». | 1 | Pendiente. Lo permite RF-FED-02. |
| 25 | Feed | H6 | No hay vista previa de la descripción: hay que entrar al detalle. | 1 | Pendiente. |
| 26 | Detalle | H1 | Mientras carga, la tarjeta está oculta y no hay indicador. | 1 | Pendiente. |
| 27 | Perfil | H1 | No se explica dónde aparece el nickname ni que el anterior queda libre. | 1 | Pendiente. |
| 28 | Página de error | H4 | Muestra el menú de visitante aunque haya sesión. | 1 | Pendiente. |

**Resumen:**
- Severidad 4: ninguno.
- **Severidad 3: 3 hallazgos (#1–#3), los tres corregidos.**
- Severidad 2: 16 hallazgos (#4–#19). De ellos, 4 corregidos (#4–#7) y 3 que se tratan en el tema 2 (#8–#10).
- Severidad 1: 9 hallazgos.

**Heurísticas sin hallazgos de severidad ≥ 2:**
- **H9:** los errores ya se muestran junto al campo, con el mensaje del SRS (RNF-USA-03).
- **H3** en los flujos de chat y reporte: siempre hay un enlace de vuelta.

## 3. Leyes de Gestalt por pantalla

Leyes revisadas:
- **Proximidad:** lo cercano se percibe como un grupo.
- **Similitud:** lo que se parece se percibe como relacionado.
- **Región común:** lo que comparte un contorno o un fondo forma un grupo.
- **Figura-fondo:** se distingue el objeto de su fondo.
- **Continuidad:** el ojo sigue líneas y alineaciones.

| Pantalla | Proximidad | Similitud | Región común | Figura-fondo | Continuidad |
|---|---|---|---|---|---|
| Iniciar sesión, Registro, Activar, Recuperar, Restablecer | Cada etiqueta pegada a su campo y la ayuda bajo él; más aire entre campos | Todos los campos con el mismo estilo; la acción principal en azul | Cada formulario en su columna centrada | **Ajustado:** el formulario sobre fondo gris claro | Campos alineados en una columna; botón al final |
| Términos | Párrafos agrupados por sección | Títulos de sección con el mismo formato | Artículo en una columna de lectura | **Ajustado:** fondo gris de página | Lectura en una columna de ancho limitado |
| Feed | **Ajustado:** etiqueta, título y autor juntos (0,35 rem); las tarjetas más separadas entre sí (1,25 rem) | **Ajustado:** color por tipo en la etiqueta y en el borde izquierdo; «Tu publicación» con estilo distinto (contorno) | Cada publicación en su tarjeta | **Ajustado:** tarjetas blancas sobre fondo gris | Rejilla regular de tarjetas |
| Detalle | Tipo y «Tu publicación» juntos; autor y tiempo restante en una línea | **Ajustado:** el tipo con el mismo color que en el feed | Tarjeta que agrupa todo el detalle y sus acciones | **Ajustado** | Acciones alineadas al pie |
| Crear publicación | Contador junto a la etiqueta de su campo | Los tres tipos como opciones iguales | El grupo de tipos en un `fieldset` | **Ajustado** | Orden de arriba abajo: tipo, título, descripción, publicar |
| Mis publicaciones | Tipo, título y tiempo restante juntos; «Cerrar» a la derecha | **Ajustado:** color por tipo | Cada publicación en su fila de lista | **Ajustado** | Filas alineadas |
| Mis chats | **Ajustado:** la hora en su propia columna, sin montarse sobre el título | Insignia «Nuevo» igual en todas las filas | Cada chat en su fila | **Ajustado** | Columna de horas alineada a la derecha |
| Chat | **Ajustado:** mensajes consecutivos del mismo autor a 0,2 rem; cambio de autor a 0,9 rem | Burbujas propias en azul y ajenas en blanco | La cabecera (interlocutor y publicación), el historial y el campo de escritura en tres zonas de la misma tarjeta | **Ajustado:** historial con fondo tintado; burbujas con sombra suave | **Ajustado:** dos columnas continuas (propio a la derecha, ajeno a la izquierda) con esquinas que enlazan los mensajes de un mismo grupo |
| Responder | **Ajustado:** la publicación a la que se responde va justo encima del formulario | **Ajustado:** etiqueta de tipo con su color | **Ajustado:** la publicación en una tarjeta propia, separada del formulario | **Ajustado** | Contexto, mensaje, imagen y enviar, de arriba abajo |
| Reportar | Cada motivo con su etiqueta | Los cinco motivos como opciones iguales | Motivos en un `fieldset` | **Ajustado** | Motivo, observación y enviar |
| Perfil | Ayuda del nickname bajo el campo | — | Formulario y enlaces separados por una línea | **Ajustado** | Una columna |

Cambios de CSS en `web/static/css/app.css`:
- Fondo de página `#f3f4f6` con superficies blancas.
- Variables `--tipo-*` por tipo de publicación.
- Separaciones internas y externas de las tarjetas del feed.
- Burbujas `.continua` en el chat.
- Rejilla `.fila-chat` en «Mis chats».

Al cambiar el fondo bajaron los contrastes: los enlaces y el botón `btn-outline-primary` de Bootstrap (#0d6efd) quedaban a 4,08:1 sobre el gris. axe-core lo detectó y se oscurecieron a #0a58ca (5,6:1). Los colores por tipo usan texto oscuro sobre fondo claro (≥ 7:1).

## 4. Verificación

`tests/e2e/navegador/test_nielsen_gestalt.py` (Playwright) mide en el navegador:
- **Similitud:** el mismo tipo comparte color y hay tres colores distintos.
- **Proximidad en el feed:** la separación interna de la tarjeta es menor que la separación entre tarjetas.
- **Figura-fondo:** el fondo de la página difiere del de la tarjeta.
- **Chat:** la separación entre mensajes consecutivos del mismo autor es menor que la de un cambio de autor; propias, ajenas e historial tienen fondos distintos.
- **Correcciones de severidad 3:** contexto al responder, aviso de cupo lleno e insignia de mensajes nuevos.

`test_accesibilidad.py` (axe-core) confirma que los cambios visuales no rompen el contraste.
