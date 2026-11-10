# WCAG 2.2 AA e internacionalización — La Banca

**Fecha:** 10 de noviembre de 2026 · **Rama:** `temas-investigacion`

## 1. WCAG 2.2 nivel AA

### 1.1 Verificación automática con axe-core

`tests/e2e/navegador/test_wcag22.py` ejecuta axe-core 4.12.1 con `runOnly` sobre los tags `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa` y `wcag22aa`:
- recorre las 17 pantallas (las 15 páginas, más la de error y la de ayuda, con y sin sesión), a 360 y 1366 px;
- no admite **ninguna** violación, de cualquier impacto.

La prueba anterior solo exigía que no hubiera violaciones serias o críticas de contraste y etiquetas.

Lo que encontró axe al ampliar los tags, ya corregido:

| Regla | Criterio WCAG | Problema | Corrección |
|---|---|---|---|
| `autocomplete-valid` | 1.3.5 Identificar el propósito de la entrada | El correo del inicio de sesión tenía `autocomplete="username email"`, que no es una combinación válida | `autocomplete="username"`, el valor que usan los gestores de contraseñas |
| `color-contrast` | 1.4.3 Contraste mínimo | Al poner fondo gris (tema 1), los enlaces y `btn-outline-primary` quedaban a 4,08:1 | #0a58ca (5,6:1) |

### 1.2 Criterios nuevos de WCAG 2.2

axe no cubre la mayoría de los criterios nuevos (solo `target-size` para 2.5.8). Por eso cada uno tiene una prueba propia en Playwright, que corre en Chromium, Firefox y WebKit.

| Criterio | Qué exige | Situación inicial | Cambio | Prueba |
|---|---|---|---|---|
| **2.4.11 Foco no oculto (mínimo)** | El elemento con foco no puede quedar totalmente tapado por otro contenido | Sin cabeceras fijas ni capas superpuestas | No hizo falta cambiar nada. La prueba se ejecuta con movimiento reducido para que el desplazamiento suave de Bootstrap no falsee la medición | `test_2_4_11_el_foco_no_queda_oculto`: recorre cada página con Tab a 360×640 px y comprueba, con `elementFromPoint` en el centro, que el foco está en pantalla y no lo tapa nada |
| **2.5.8 Tamaño del objetivo (mínimo)** | Objetivos de al menos 24×24 px, salvo enlaces dentro de una frase | Casillas y radios de 16 px; enlaces sueltos de 19–21 px de alto («← Volver al feed», «Volver a iniciar sesión», títulos en «Mis publicaciones», enlaces del pie) | Casillas y radios de 24 px alineados con su etiqueta; enlaces sueltos `inline-block` de 24 px | axe `target-size` + `test_2_5_8_objetivos_de_al_menos_24_px`, que mide todos los controles (incluido el menú desplegado en móvil) |
| **3.2.6 Ayuda consistente** | El mecanismo de ayuda aparece en el mismo orden relativo en todas las páginas | No había ayuda (también era el hallazgo H10 de Nielsen) | Nueva página `/ayuda` con preguntas frecuentes (activación, duración de publicaciones y chats, reportes, contraseña, datos personales). Está enlazada en el pie de todas las páginas, siempre después de «Términos» | `test_3_2_6_ayuda_en_el_mismo_lugar` |
| **3.3.7 Entrada redundante** | No pedir de nuevo, en el mismo proceso, un dato ya ingresado | El correo se escribía de nuevo al pasar del registro a la activación, al inicio de sesión o a la recuperación | Los campos con `data-recordar="correo"` guardan el valor en `sessionStorage` (solo la pestaña actual, se borra al cerrarla) y lo proponen si el campo está vacío | `test_3_3_7_el_correo_no_se_vuelve_a_escribir` |
| **3.3.8 Autenticación accesible (mínimo)** | Iniciar sesión sin pruebas cognitivas: se puede pegar y usar un gestor de contraseñas | Ya se permitía pegar; faltaba revisar los valores de `autocomplete` | `autocomplete` correcto en todos los campos de credenciales (`username`, `email`, `current-password`, `new-password`); ningún `onpaste` ni bloqueo del pegado | `test_3_3_8_autenticacion_accesible`: valores de `autocomplete`, evento `paste` no cancelado e inserción de texto como la de un gestor |

**Criterios de 2.2 que no aplican:**
- **2.5.7 Movimientos de arrastre:** la app no usa arrastrar.
- **3.3.9 Autenticación accesible (mejorado):** es AAA.
- **2.4.12 Foco no oculto (mejorado):** es AAA.

## 2. Internacionalización

### 2.1 Arquitectura

| Pieza | Archivo | Función |
|---|---|---|
| Catálogo | `web/i18n/es-PE.json` | Todos los textos de las plantillas y del JS, anidados por pantalla, con interpolación `{nombre}`. Las claves bajo `js` son las que usa el navegador. |
| Servidor | `app/shared/web/i18n.py` | `t("clave", nombre=valor)`; `IDIOMA_ACTIVO = "es-PE"`; `IDIOMAS_DISPONIBLES = ("es-PE",)`; `ZONA_HORARIA = "America/Lima"`. |
| Plantillas | `app/shared/web/plantillas.py` | `t`, `idioma` y `catalogo_js` son globales de Jinja. Todas las páginas usan `<html lang="es-PE">`. |
| Navegador | `web/static/js/app.js` | `Banca.t(clave, parámetros)` lee el catálogo que la página incrusta en `<script id="i18n" type="application/json">`. |
| Fechas y horas | `Banca.formatoHora` y `Banca.formatoFecha` | `Intl.DateTimeFormat("es-PE", { timeZone: "America/Lima" })`. La hora de los mensajes (HH:MM, 24 h) y la fecha de los términos («1 de noviembre de 2026») se muestran en Lima aunque el dispositivo esté en otra zona (RN-34). |

**Un solo idioma, como pide el SRS:** RNF-USA-05 exige la interfaz en español, así que es-PE es el único idioma activo.

**Agregar otro idioma** solo requiere copiar `es-PE.json` con las mismas claves traducidas y añadirlo a `IDIOMAS_DISPONIBLES`. `test_listo_para_otro_idioma` lo demuestra con un catálogo de prueba. Lo que faltaría para ofrecerlo: elegir el idioma por usuario (preferencia o `Accept-Language`) y traducir los textos que siguen fuera del catálogo (2.3).

**Selector de imagen:** el control nativo `<input type="file">` muestra textos del navegador («Choose File / No file chosen» en un navegador en inglés). Se reemplazó la parte visible por un botón y un nombre de archivo tomados del catálogo («Elegir imagen», «Ningún archivo seleccionado»). El `<input>` real queda superpuesto y transparente: conserva la etiqueta, el foco y el teclado, y el foco se dibuja en el botón visible.

### 2.2 Verificación

Unitarias, en `tests/web/test_i18n.py`:
- todas las claves usadas en las plantillas y en el JS existen en el catálogo, incluidas las compuestas (`tipos.*`, `motivos.*`, `error.*`, `ayuda.*`);
- **ninguna plantilla tiene texto visible literal**: tras quitar etiquetas HTML y expresiones Jinja no queda ninguna palabra, y ningún `placeholder`, `aria-label`, `title` ni `alt` es literal;
- **ningún JS tiene literales de interfaz.** Es una heurística: marca como sospechoso todo literal con tildes, ñ, ¿, ¡ o palabras con mayúscula inicial, salvo valores técnicos (`Accept`, métodos HTTP, selectores, rutas). Detecta los textos de la versión anterior de `chat.js`, aunque puede pasar por alto algún caso límite;
- las páginas usan `lang="es-PE"` y llevan el catálogo incrustado;
- con Node y la zona del sistema en `Asia/Tokyo`, `UTC` o `America/Lima`, `formatoHora("2026-10-03T03:30:00Z")` da «22:30» y `formatoFecha("2026-11-01")` da «1 de noviembre de 2026».

En navegador, `test_i18n_selector_de_imagen_y_hora_en_lima` comprueba con un navegador en `en-US` y zona `Asia/Tokyo`:
- el selector muestra los textos del catálogo y el nombre del archivo elegido;
- la hora del mensaje coincide con la que calcula el servidor en America/Lima.

### 2.3 Fuera del catálogo (límites)

- **Mensajes de la API:** los errores y confirmaciones que devuelve el servidor (por ejemplo «Correo o contraseña incorrectos») siguen en los handlers de Python. Son los textos literales que fija el SRS y forman parte del contrato de la API. Para un segundo idioma habría que pasarlos al catálogo con claves por código de error.
- **Correos de activación y recuperación:** su texto está en `app/shared/email/sender.py`.
- **Texto legal:** `web/terminos/terminos.txt` es un documento por versión; un segundo idioma necesitaría su propio archivo.
- **`sessionStorage`:** solo guarda el correo, en la pestaña actual, y no persiste al cerrarla.
