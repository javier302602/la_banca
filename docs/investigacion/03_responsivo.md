# Diseño responsivo y base para Figma — La Banca

**Fecha:** 10 de noviembre de 2026 · **Rama:** `temas-investigacion`

## 1. Mobile-first con tres anchos de diseño

`web/static/css/app.css` define primero los estilos para 360 px y luego los amplía con `@media (min-width: 768px)` y `@media (min-width: 1024px)`. No hay ninguna consulta `max-width`.

| Ancho de diseño | Dispositivo de referencia | Menú | Feed | Formularios y lecturas | Títulos de página |
|---|---|---|---|---|---|
| **360 px** (base) | Teléfono (RNF-USA-02) | Colapsado tras el botón de menú | 1 columna | Todo el ancho disponible | 20 px |
| **768 px** | Tableta vertical | Expandido | 2 columnas | Centrados: estrecho 30 rem, medio 40 rem, ancho 48 rem | 24 px |
| **1024 px** | Escritorio / tableta horizontal | Expandido | 3 columnas | Medio pasa a 44 rem | 24 px |

**Cambios:**
- **Contenedores propios.** La rejilla de Bootstrap (`row`/`col-md-*`/`col-lg-*`, cuyo `lg` es 992 px y no 1024) y los `style="max-width: …"` en línea se reemplazaron por tres contenedores:
  - `contenedor-estrecho`: formularios de acceso, perfil, reportar y página de error.
  - `contenedor-medio`: crear publicación, detalle y responder.
  - `contenedor-ancho`: chat, términos y ayuda.
- **Feed.** Pasa a `rejilla-feed`, una rejilla CSS de 1, 2 y 3 columnas.
- **Chat.** El historial ocupa el 55 % del alto en móvil y el 60 % desde 768 px; las burbujas, el 85 % del ancho en móvil y el 75 % desde 768 px.
- **Títulos.** La escala de tokens sustituye al tamaño fluido de `.h4` de Bootstrap (que daba 21,48 px a 360 px).
- **Menú.** Se mantiene `navbar-expand-md`: Bootstrap ya expande a partir de 768 px.

## 2. Tokens de diseño

**Fuente única:** `web/static/css/tokens.css` (v2: `:root` define el modo claro y `[data-bs-theme="dark"]` el oscuro, con los mismos nombres; el JSON tiene los conjuntos `global`, `claro` y `oscuro` y los temas Claro y Oscuro), con variables `--lb-<categoría>-<nombre>` (48 tokens). `app.css` solo usa tokens: no tiene ningún color literal, y un test lo comprueba. Bootstrap también se alimenta de ellos (`--bs-body-color`, `--bs-link-color`, `--bs-secondary-color`…).

| Categoría | Tokens | Ejemplos |
|---|---|---|
| Color | 23 | `primario` #0a58ca, `peligro` #b02a37, `fondo` #f3f4f6, `superficie` #fff, `texto-secundario` #5c636a, `necesito-*`, `ofrezco-*` y `actividad-*` (fondo, texto y borde por tipo) |
| Tipografía | 10 | Familia de sistema; tamaños xs 12, sm 14, base 16, lg 20 y xl 24 px; pesos 400 y 600; interlineado 1,5 y 1,25 |
| Espaciado | 7 | Escala de 4 px: 4, 8, 12, 16, 20, 24 y 32 px |
| Radios | 4 | 4, 8, 16 px y píldora |
| Tamaños | 4 | Puntos de quiebre 360, 768 y 1024 px; objetivo mínimo de 24 px (WCAG 2.5.8) |

Cada color lleva en un comentario su contraste sobre el fondo en que se usa. Ese comentario pasa a la `description` del token en Figma.

### Exportación para Figma (Tokens Studio)

`python scripts/exportar_tokens.py` genera `docs/investigacion/tokens.json` en el formato de Tokens Studio para Figma:
- conjunto `global`, con grupos `color`, `fontFamilies`, `fontSizes`, `fontWeights`, `lineHeights`, `spacing`, `borderRadius` y `sizing`;
- cada token con `value`, `type` y `description`;
- `$themes` y `$metadata.tokenSetOrder`.

Con `--comprobar`, el script falla si el JSON no coincide con el CSS; `tests/web/test_tokens.py` hace la misma comprobación en la suite.

Para importarlo en Figma:
1. Instalar el plugin **Tokens Studio for Figma**.
2. En *Settings → Sync providers*, conectar el repositorio (GitHub) apuntando a `docs/investigacion/tokens.json`, o usar *Tools → Load from file / folder*.
3. Activar el conjunto `global`. Los valores en rem se convierten con la base de 16 px (*Settings → Base font size*).
4. *Styles & Variables → Create variables / Create styles* genera las variables y estilos de Figma.

El flujo inverso (diseño → código) sería: editar en Tokens Studio, exportar el JSON y trasladar los cambios a `tokens.css`. Ese paso no está automatizado; el test de sincronía avisa si el JSON y el CSS se separan.

## 3. Capturas

`python scripts/tomar_capturas.py` arranca la app contra MongoDB (replica set), siembra datos de ejemplo y captura con Playwright (Chromium) la página completa de las 15 pantallas en los tres anchos y en los dos modos (emulando `prefers-color-scheme`): 90 imágenes en `docs/investigacion/capturas/claro/` y `docs/investigacion/capturas/oscuro/`, con nombre `<nn>-<página>-<ancho>.png`. La tabla enlaza el modo claro; el oscuro tiene los mismos nombres en `capturas/oscuro/`.

| # | Página | 360 px | 768 px | 1024 px |
|---|---|---|---|---|
| 01 | Iniciar sesión | [ver](capturas/claro/01-login-360.png) | [ver](capturas/claro/01-login-768.png) | [ver](capturas/claro/01-login-1024.png) |
| 02 | Registro | [ver](capturas/claro/02-registro-360.png) | [ver](capturas/claro/02-registro-768.png) | [ver](capturas/claro/02-registro-1024.png) |
| 03 | Activar cuenta | [ver](capturas/claro/03-activar-360.png) | [ver](capturas/claro/03-activar-768.png) | [ver](capturas/claro/03-activar-1024.png) |
| 04 | Recuperar contraseña | [ver](capturas/claro/04-recuperar-360.png) | [ver](capturas/claro/04-recuperar-768.png) | [ver](capturas/claro/04-recuperar-1024.png) |
| 05 | Restablecer contraseña | [ver](capturas/claro/05-restablecer-360.png) | [ver](capturas/claro/05-restablecer-768.png) | [ver](capturas/claro/05-restablecer-1024.png) |
| 06 | Términos | [ver](capturas/claro/06-terminos-360.png) | [ver](capturas/claro/06-terminos-768.png) | [ver](capturas/claro/06-terminos-1024.png) |
| 07 | Feed «Ahora» | [ver](capturas/claro/07-feed-360.png) | [ver](capturas/claro/07-feed-768.png) | [ver](capturas/claro/07-feed-1024.png) |
| 08 | Detalle | [ver](capturas/claro/08-detalle-360.png) | [ver](capturas/claro/08-detalle-768.png) | [ver](capturas/claro/08-detalle-1024.png) |
| 09 | Crear publicación | [ver](capturas/claro/09-crear-publicacion-360.png) | [ver](capturas/claro/09-crear-publicacion-768.png) | [ver](capturas/claro/09-crear-publicacion-1024.png) |
| 10 | Mis publicaciones | [ver](capturas/claro/10-mis-publicaciones-360.png) | [ver](capturas/claro/10-mis-publicaciones-768.png) | [ver](capturas/claro/10-mis-publicaciones-1024.png) |
| 11 | Mis chats | [ver](capturas/claro/11-mis-chats-360.png) | [ver](capturas/claro/11-mis-chats-768.png) | [ver](capturas/claro/11-mis-chats-1024.png) |
| 12 | Chat | [ver](capturas/claro/12-chat-360.png) | [ver](capturas/claro/12-chat-768.png) | [ver](capturas/claro/12-chat-1024.png) |
| 13 | Responder | [ver](capturas/claro/13-responder-360.png) | [ver](capturas/claro/13-responder-768.png) | [ver](capturas/claro/13-responder-1024.png) |
| 14 | Reportar | [ver](capturas/claro/14-reportar-360.png) | [ver](capturas/claro/14-reportar-768.png) | [ver](capturas/claro/14-reportar-1024.png) |
| 15 | Perfil | [ver](capturas/claro/15-perfil-360.png) | [ver](capturas/claro/15-perfil-768.png) | [ver](capturas/claro/15-perfil-1024.png) |

Las capturas sirven de referencia para maquetar en Figma con los mismos tokens; también permiten comparar visualmente después de cada cambio de estilos.

## 4. Verificación

- **`tests/web/test_tokens.py`:**
  - el JSON está sincronizado con el CSS y respeta el formato de Tokens Studio;
  - `app.css` no tiene colores literales y solo usa tokens que existen;
  - las únicas media queries son `min-width` 768 y 1024;
  - `tokens.css` se carga antes que `app.css`;
  - no quedan columnas de Bootstrap ni anchos en línea.
- **`tests/e2e/navegador/test_responsivo.py`** (Playwright, tres motores):
  - el feed tiene 1, 2 y 3 columnas a 360, 768 y 1024 px;
  - ninguna de las 17 pantallas se desborda en horizontal en ningún ancho;
  - el menú está colapsado solo a 360 px;
  - los títulos miden 20 y 24 px;
  - el formulario ocupa todo el ancho en móvil y se limita a 30 rem desde 768 px.
