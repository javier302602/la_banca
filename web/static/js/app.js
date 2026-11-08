/* La Banca — utilidades comunes (Fetch API, tiempos, DOM seguro).
 * Todo texto de usuario se inserta con textContent: nunca se interpreta como HTML (RNF-SEG-05). */
"use strict";

const Banca = (() => {
  const CABECERA_AUTOMATICA = { "X-Actualizacion-Automatica": "1" };  // RF-AUT-25
  const TIPOS = { NECESITO: "Necesito", OFREZCO: "Ofrezco", ACTIVIDAD: "Actividad" };
  let desfase = 0;  // ms entre la hora del servidor y la del navegador (RF-FED-09: hora del sistema)

  class ErrorApi extends Error {
    constructor(status, datos) {
      super((datos && datos.detail) || "Ocurrió un error. Inténtalo de nuevo");
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
      throw new ErrorApi(0, { detail: "Sin conexión. Revisa tu red e inténtalo de nuevo" });
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

  function restante(fechaIso) {
    const ms = new Date(fechaIso).getTime() - ahora();
    if (ms <= 0) return "Expirada";
    const minutos = Math.ceil(ms / 60000);
    const h = Math.floor(minutos / 60), m = minutos % 60;
    return h > 0 ? `${h} h ${m} min` : `${m} min`;
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

  function contador(campo, salida, maximo) {  // RF-PUB-12
    const actualizar = () => { salida.textContent = `${campo.value.trim().length}/${maximo}`; };
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
    catch (e) { throw new ErrorApi(422, { detail: "La imagen está dañada o no se puede leer" }); }
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
    throw new ErrorApi(422, { detail: "No se pudo reducir la imagen por debajo de 4 MB" });
  }

  setInterval(() => refrescarRestantes(), 30000);

  document.addEventListener("click", async (evento) => {
    const boton = evento.target.closest("[data-cerrar-sesion]");
    if (!boton) return;
    evento.preventDefault();
    try { await api("/api/sesiones/cerrar", { metodo: "POST" }); } catch (e) { /* se redirige igual */ }
    location.href = "/login";
  });

  return { api, ErrorApi, TIPOS, sincronizar, ahora, restante, el, alerta, limpiar, contador,
           refrescarRestantes, ocupado, parametro, comprimirImagen, LIMITE_SUBIDA };
})();
