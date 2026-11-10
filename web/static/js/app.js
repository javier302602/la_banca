/* La Banca — utilidades comunes (Fetch API, tiempos, DOM seguro).
 * Todo texto de usuario se inserta con textContent: nunca se interpreta como HTML (RNF-SEG-05). */
"use strict";

const Banca = (() => {
  const CABECERA_AUTOMATICA = { "X-Actualizacion-Automatica": "1" };  // RF-AUT-25
  let desfase = 0;  // ms entre la hora del servidor y la del navegador (RF-FED-09: hora del sistema)

  /* i18n: los textos vienen del catálogo es-PE que la página incrusta en <script id="i18n"> (claves «js.*» de
   * web/i18n/es-PE.json). Idioma y zona horaria fijos por el SRS: es-PE y America/Lima (RN-34). */
  const IDIOMA = "es-PE";
  const ZONA_HORARIA = "America/Lima";
  let catalogo = null;

  function cargarCatalogo() {
    if (catalogo) return catalogo;
    const nodo = typeof document.getElementById === "function" ? document.getElementById("i18n") : null;
    catalogo = nodo ? JSON.parse(nodo.textContent) : {};
    return catalogo;
  }

  function t(clave, parametros = {}) {
    const texto = cargarCatalogo()[clave];
    if (texto === undefined) return clave;  // clave faltante: visible para detectarla en pruebas
    return texto.replace(/\{(\w+)\}/g, (todo, nombre) => (nombre in parametros ? String(parametros[nombre]) : todo));
  }

  const TIPOS = new Proxy({}, { get: (_, tipo) => t(`tipos.${String(tipo)}`) });

  const FORMATO_HORA = new Intl.DateTimeFormat(IDIOMA, { timeZone: ZONA_HORARIA, hour: "2-digit", minute: "2-digit",
                                                         hourCycle: "h23" });
  const FORMATO_FECHA = new Intl.DateTimeFormat(IDIOMA, { timeZone: ZONA_HORARIA, dateStyle: "long" });

  function formatoHora(fechaIso) { return FORMATO_HORA.format(new Date(fechaIso)); }  // RF-CHT-11: HH:MM en Lima

  function formatoFecha(fecha) {  // «AAAA-MM-DD» se interpreta como ese día en Lima, no en UTC
    const valor = /^\d{4}-\d{2}-\d{2}$/.test(fecha) ? `${fecha}T12:00:00-05:00` : fecha;
    const d = new Date(valor);
    return Number.isNaN(d.getTime()) ? String(fecha) : FORMATO_FECHA.format(d);
  }

  class ErrorApi extends Error {
    constructor(status, datos) {
      super((datos && datos.detail) || t("error_generico"));
      this.status = status;
      this.codigo = datos && datos.codigo;
      this.datos = datos || {};
    }
  }

  function sincronizar(ahoraServidor) {
    if (ahoraServidor) desfase = new Date(ahoraServidor).getTime() - Date.now();
  }

  function ahora() { return Date.now() + desfase; }

  async function api(url, { metodo = "GET", cuerpo, formulario, automatica = false } = {}) {
    const headers = { Accept: "application/json" };
    if (automatica) Object.assign(headers, CABECERA_AUTOMATICA);
    let body;
    if (formulario) body = formulario;
    else if (cuerpo !== undefined) { headers["Content-Type"] = "application/json"; body = JSON.stringify(cuerpo); }
    let respuesta;
    try {
      respuesta = await fetch(url, { method: metodo, headers, body, credentials: "same-origin" });
    } catch (e) {
      throw new ErrorApi(0, { detail: t("sin_conexion") });
    }
    let datos = null;
    if (respuesta.status !== 204) {
      try { datos = await respuesta.json(); } catch (e) { datos = null; }
    }
    if (respuesta.status === 401 && !url.startsWith("/api/sesiones")) {
      location.href = "/login" + (datos && datos.codigo === "sesion_expirada" ? "?motivo=inactividad" : "");
      throw new ErrorApi(401, datos);
    }
    if (!respuesta.ok) throw new ErrorApi(respuesta.status, datos);
    if (datos && datos.ahora) sincronizar(datos.ahora);
    return datos;
  }

  function restante(fechaIso) {  // RNF-USA-01: «X h Y min», «X h», «Y min» o «menos de 1 min»
    const ms = new Date(fechaIso).getTime() - ahora();
    if (ms <= 0) return t("tiempo.expirada");
    const minutos = Math.floor(ms / 60000);
    if (minutos < 1) return t("tiempo.menos_de_un_minuto");
    const h = Math.floor(minutos / 60), m = minutos % 60;
    if (h === 0) return t("tiempo.minutos", { m });
    return m === 0 ? t("tiempo.horas", { h }) : t("tiempo.horas_minutos", { h, m });
  }

  function el(etiqueta, atributos = {}, ...hijos) {
    const nodo = document.createElement(etiqueta);
    for (const [clave, valor] of Object.entries(atributos)) {
      if (valor === null || valor === undefined || valor === false) continue;
      if (clave === "class") nodo.className = valor;
      else if (clave === "text") nodo.textContent = valor;
      else if (clave.startsWith("on")) nodo.addEventListener(clave.slice(2), valor);
      else nodo.setAttribute(clave, valor === true ? "" : valor);
    }
    for (const hijo of hijos) if (hijo !== null && hijo !== undefined) nodo.append(hijo);
    return nodo;
  }

  function alerta(contenedor, mensaje, tipo = "danger", ...extras) {
    if (!contenedor) return;
    contenedor.replaceChildren(el("div", { class: `alert alert-${tipo}`, role: "alert" }, el("span", { text: mensaje }), ...extras));
  }

  function limpiar(contenedor) { if (contenedor) contenedor.replaceChildren(); }

  /* RNF-USA-03: el mensaje de un dato inválido se muestra junto al campo, enlazado con aria-describedby.
   * El servidor indica el campo en `errores[].campo` (validación) o en `campo` (errores de dominio). */
  function limpiarErrores(formulario) {
    formulario.querySelectorAll("[data-error-de]").forEach((n) => n.remove());
    formulario.querySelectorAll("[aria-invalid]").forEach((campo) => {
      campo.removeAttribute("aria-invalid");
      campo.classList.remove("is-invalid");
      const ids = (campo.getAttribute("aria-describedby") || "").split(" ").filter((i) => i && !i.startsWith("error-"));
      if (ids.length) campo.setAttribute("aria-describedby", ids.join(" ")); else campo.removeAttribute("aria-describedby");
    });
  }

  function errorEnCampo(formulario, nombre, mensaje) {
    const campos = nombre ? [...formulario.querySelectorAll(`[name="${CSS.escape(nombre)}"]`)] : [];
    if (!campos.length) return null;
    const id = `error-${nombre}`;
    formulario.querySelectorAll(`[data-error-de="${CSS.escape(nombre)}"]`).forEach((n) => n.remove());
    const aviso = el("div", { class: "invalid-feedback d-block", id, "data-error-de": nombre, text: mensaje });
    const grupo = campos[0].type === "radio" ? campos[0].closest("fieldset") : null;
    if (grupo) grupo.append(aviso); else campos[0].insertAdjacentElement("afterend", aviso);
    for (const campo of campos) {
      campo.setAttribute("aria-invalid", "true");
      if (!grupo) campo.classList.add("is-invalid");
      const ids = (campo.getAttribute("aria-describedby") || "").split(" ").filter(Boolean);
      if (!ids.includes(id)) campo.setAttribute("aria-describedby", [...ids, id].join(" "));
    }
    return campos[0];
  }

  /* Muestra los errores de un ErrorApi junto a sus campos. Devuelve true si ubicó alguno; si no, el llamador
   * muestra el mensaje general. `general` es el campo para los errores de validación sin campo propio. */
  function mostrarErrores(formulario, error, { general = null } = {}) {
    limpiarErrores(formulario);
    const datos = (error && error.datos) || {};
    let primero = null;
    for (const e of datos.errores || []) {
      const campo = errorEnCampo(formulario, e.campo || general, e.mensaje);
      primero = primero || campo;
    }
    if (!primero && datos.campo) primero = errorEnCampo(formulario, datos.campo, error.message);
    if (primero) primero.focus();
    return Boolean(primero);
  }

  function vaciarContrasenas(formulario) {  // RNF-USA-06: tras un error solo se vacían las contraseñas
    formulario.querySelectorAll('input[type="password"]').forEach((campo) => { campo.value = ""; });
  }

  function contador(campo, salida, maximo) {  // RF-PUB-12
    const actualizar = () => { salida.textContent = t("contador", { usados: campo.value.trim().length, maximo }); };
    campo.addEventListener("input", actualizar);
    actualizar();
  }

  function refrescarRestantes(raiz = document) {  // RF-FED-09: al menos una vez por minuto
    raiz.querySelectorAll("[data-expira]").forEach((n) => { n.textContent = restante(n.dataset.expira); });
  }

  function ocupado(boton, estado) {
    if (!boton) return;
    boton.disabled = estado;
    if (estado) boton.setAttribute("aria-busy", "true"); else boton.removeAttribute("aria-busy");
  }

  function parametro(nombre) { return new URLSearchParams(location.search).get(nombre); }

  /* Vercel admite solicitudes de hasta 4.5 MB: una imagen de más de 4 MB se redimensiona y se vuelve a
   * codificar con canvas (WebP si el navegador lo soporta, si no JPEG) antes de subirla. El servidor
   * conserva su validación (≤ 5 MB) y la recodificación con Pillow. */
  const LIMITE_SUBIDA = 4 * 1024 * 1024;
  const LADO_MAXIMO = 2560;

  function formatoSalida(lienzo) {
    lienzo.width = lienzo.height = 1;
    return String(lienzo.toDataURL("image/webp")).startsWith("data:image/webp") ? "image/webp" : "image/jpeg";
  }

  async function comprimirImagen(archivo, limite = LIMITE_SUBIDA) {
    if (!archivo || archivo.size <= limite) return archivo;
    let mapa;
    try { mapa = await createImageBitmap(archivo); }
    catch (e) { throw new ErrorApi(422, { detail: t("imagen.danada") }); }
    const lienzo = document.createElement("canvas");
    const formato = formatoSalida(lienzo);
    let escala = Math.min(1, LADO_MAXIMO / Math.max(mapa.width, mapa.height));
    let calidad = 0.85;
    try {
      for (let intento = 0; intento < 10; intento++) {
        lienzo.width = Math.max(1, Math.round(mapa.width * escala));
        lienzo.height = Math.max(1, Math.round(mapa.height * escala));
        lienzo.getContext("2d").drawImage(mapa, 0, 0, lienzo.width, lienzo.height);
        const blob = await new Promise((resolver) => lienzo.toBlob(resolver, formato, calidad));
        if (blob && blob.size <= limite) {
          const nombre = (archivo.name || "imagen").replace(/\.[^.]*$/, "") + (formato === "image/webp" ? ".webp" : ".jpg");
          return new File([blob], nombre, { type: formato });
        }
        if (calidad > 0.6) calidad = Math.round((calidad - 0.1) * 100) / 100; else escala *= 0.75;
      }
    } finally {
      if (mapa.close) mapa.close();
    }
    throw new ErrorApi(422, { detail: t("imagen.no_reducible") });
  }

  setInterval(() => refrescarRestantes(), 30000);

  /* Nielsen H1: el menú indica cuántos chats tienen mensajes sin leer (los chats expiran tras 24 h sin
   * mensajes; sin este aviso solo se veían entrando en «Mis chats»). Sondeo automático: no reinicia la
   * inactividad de la sesión (RF-AUT-25). */
  async function actualizarNoLeidos() {
    const insignia = document.getElementById("nav-no-leidos");
    try {
      const r = await api("/api/chats", { automatica: true });
      const n = r.items.filter((c) => c.no_leidos).length;
      insignia.textContent = n ? t(n === 1 ? "no_leidos.uno" : "no_leidos.varios", { n }) : "";
      insignia.classList.toggle("d-none", n === 0);
      insignia.dataset.cargado = "1";
    } catch (e) { /* informativo */ }
  }
  /* Selector de imagen propio: el texto del control nativo depende del idioma del navegador («Choose File»);
   * el botón visible y el nombre del archivo salen del catálogo. El <input> real sigue siendo el control
   * accesible (etiqueta, foco y teclado) y queda superpuesto, transparente, sobre el botón visible. */
  function prepararSelectorArchivo(raiz = document) {
    raiz.querySelectorAll(".selector-archivo").forEach((caja) => {
      const entrada = caja.querySelector("input[type=file]");
      const nombre = caja.querySelector(".nombre-archivo");
      const mostrar = () => { nombre.textContent = entrada.files.length ? entrada.files[0].name : t("imagen.ninguna"); };
      entrada.addEventListener("change", mostrar);
      entrada.closest("form")?.addEventListener("reset", () => setTimeout(mostrar));
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    // Fechas visibles formateadas con Intl en America/Lima (p. ej. la versión de los términos)
    document.querySelectorAll("time[data-fecha]").forEach((n) => { n.textContent = formatoFecha(n.getAttribute("datetime")); });
    prepararSelectorArchivo();
    // WCAG 3.3.7 (entrada redundante): el correo escrito en un paso se propone en el siguiente
    // (registro → activación → inicio de sesión → recuperación). Solo en sessionStorage de esta pestaña.
    document.querySelectorAll("[data-recordar]").forEach((campo) => {
      const clave = `banca.${campo.dataset.recordar}`;
      try { if (!campo.value) campo.value = sessionStorage.getItem(clave) || ""; } catch (e) { /* sin almacenamiento */ }
      campo.addEventListener("change", () => { try { sessionStorage.setItem(clave, campo.value.trim()); } catch (e) { /* */ } });
    });
    if (!document.getElementById("nav-no-leidos")) return;  // sin sesión no hay menú de chats
    actualizarNoLeidos();
    setInterval(() => { if (document.visibilityState === "visible") actualizarNoLeidos(); }, 30000);
  });

  document.addEventListener("click", async (evento) => {
    const boton = evento.target.closest("[data-cerrar-sesion]");
    if (!boton) return;
    evento.preventDefault();
    try { await api("/api/sesiones/cerrar", { metodo: "POST" }); } catch (e) { /* se redirige igual */ }
    location.href = "/login";
  });

  return { api, ErrorApi, TIPOS, t, formatoHora, formatoFecha, IDIOMA, ZONA_HORARIA, sincronizar, ahora, restante, el,
           alerta, limpiar, contador,
           limpiarErrores, errorEnCampo, mostrarErrores, vaciarContrasenas,
           refrescarRestantes, ocupado, parametro, comprimirImagen, LIMITE_SUBIDA };
})();
