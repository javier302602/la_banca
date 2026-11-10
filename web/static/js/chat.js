/* M04 — Chat: responder (CU-10), enviar mensaje (CU-11), mis chats y chat abierto (CU-12, EA-04).
 * El sondeo de 1 s solo corre en la página de un chat abierto y visible. */
"use strict";

(() => {
  const { api, alerta, limpiar, el, contador, ocupado, mostrarErrores, limpiarErrores, TIPOS, t, formatoHora, etiquetaTipo, autor, avatar, icono } = Banca;
  const pagina = document.body.dataset.pagina;
  const mensajes = document.getElementById("mensajes");

  async function datosMensaje() {
    const texto = document.getElementById("texto").value;
    const original = document.getElementById("imagen").files[0];
    const invalido = (detail) => new Banca.ErrorApi(422, { detail, errores: [{ campo: "texto", mensaje: detail }] });
    if (texto.trim() && original) throw invalido(t("chat.texto_o_imagen"));
    if (!texto.trim() && !original) throw invalido(t("chat.vacio"));
    const datos = new FormData();
    if (original) datos.append("imagen", await Banca.comprimirImagen(original)); else datos.append("texto", texto);
    return datos;
  }

  if (pagina === "responder") {
    const id = encodeURIComponent(document.getElementById("publicacion").dataset.id);
    const formulario = document.getElementById("form-mensaje");
    // Nielsen H6 (reconocer en vez de recordar): se muestra la publicación a la que se responde
    api(`/api/publicaciones/${id}`).then((p) => {
      document.getElementById("contexto-autor").replaceChildren(autor(p.nickname_autor, p.apariencia_autor));
      const tipo = document.getElementById("contexto-tipo");
      tipo.replaceChildren(...etiquetaTipo(p.tipo));
      tipo.classList.add(`tipo-${p.tipo}`);
      document.getElementById("contexto-titulo").textContent = p.titulo;
      document.getElementById("contexto-descripcion").textContent = p.descripcion;
      document.getElementById("contexto").classList.remove("d-none");
    }).catch((error) => {
      if (error.status === 401) return;
      alerta(mensajes, error.message, error.status === 410 ? "secondary" : "danger");
      if (error.status === 410) formulario.querySelectorAll("textarea, input, button").forEach((n) => { n.disabled = true; });
    });
    contador(document.getElementById("texto"), document.getElementById("contador-texto"), 500);
    formulario.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      const boton = formulario.querySelector("[type=submit]");
      ocupado(boton, true);
      limpiarErrores(formulario);
      try {
        const r = await api(`/api/publicaciones/${id}/respuestas`, { metodo: "POST", formulario: await datosMensaje() });
        location.href = `/chats/${encodeURIComponent(r.chat_id)}`;
      } catch (error) {
        const extra = error.datos.chat_id  // RF-CHT-23
          ? [" ", el("a", { class: "alert-link", href: `/chats/${encodeURIComponent(error.datos.chat_id)}`, text: t("chat.abrir_chat") })] : [];
        // RNF-USA-03: los errores del contenido van junto al mensaje; los demás, en el aviso general
        if (!extra.length && mostrarErrores(formulario, error, { general: "texto" })) limpiar(mensajes);
        else alerta(mensajes, error.message, "danger", ...extra);
      } finally { ocupado(boton, false); }
    });
  }

  if (pagina === "mis-chats") {
    const lista = document.getElementById("lista");
    const vacio = document.getElementById("vacio");
    const fila = (c) => el("a", { class: "list-group-item list-group-item-action fila-chat",
                                  href: `/chats/${encodeURIComponent(c.id)}` },
      el("div", { class: "d-flex gap-2 align-items-start" }, avatar(c.apariencia_contraparte, "md"), el("div", {},
        el("div", { class: "fw-semibold", text: c.nickname_contraparte }),
        el("div", { class: "small text-body-secondary", text: `${TIPOS[c.tipo_publicacion]}${t("separador")}${c.titulo_publicacion}` }))),
      el("div", { class: "text-end" },
        el("div", { class: "small text-body-secondary", text: formatoHora(c.ultimo_mensaje_en) }),
        c.no_leidos ? el("span", { class: "badge text-bg-primary", text: t("chat.nuevo") }) : null));  // RF-CHT-21
    const cargar = async (automatica = false) => {
      try {
        const r = await api("/api/chats", { automatica });
        lista.replaceChildren(...r.items.map(fila));
        vacio.classList.toggle("d-none", r.items.length > 0);
      } catch (error) { if (error.status !== 401) alerta(mensajes, error.message); }
    };
    cargar();
    setInterval(() => { if (document.visibilityState === "visible") cargar(true); }, 30000);
  }

  if (pagina === "chat") {
    const chatId = encodeURIComponent(document.getElementById("chat-id").dataset.id);
    const seccion = document.getElementById("chat");
    const historial = document.getElementById("historial");
    const aviso = document.getElementById("aviso");
    const formulario = document.getElementById("form-mensaje");
    const texto = document.getElementById("texto");
    const entradaImagen = document.getElementById("imagen");
    const entradaDocumento = document.getElementById("documento");
    const adjuntoElegido = document.getElementById("adjunto-elegido");
    const vistos = new Set();
    let ultimo = null, temporizador = null, expirado = false;
    let anterior = null;            // { propio, fila } del último mensaje pintado (agrupación)
    let aparienciaOtra = null;      // foto, avatar o iniciales de la otra persona
    let vistoHasta = null;          // lastReadAt de la otra persona (SRS v2.0: enviado / visto)
    let adjunto = null;             // { tipo: "imagen" | "documento", archivo }
    contador(texto, document.getElementById("contador-texto"), 500);

    const TAMANO = new Intl.NumberFormat(Banca.IDIOMA, { maximumFractionDigits: 1 });
    function tamanoLegible(bytes) {
      if (bytes < 1024) return t("tamano.bytes", { n: bytes });
      if (bytes < 1024 * 1024) return t("tamano.kb", { n: TAMANO.format(bytes / 1024) });
      return t("tamano.mb", { n: TAMANO.format(bytes / (1024 * 1024)) });
    }

    function contenido(m) {
      if (m.imagen_url) return el("img", { src: m.imagen_url, alt: t("imagen.alt", { nickname: m.nickname_emisor }), loading: "lazy" });
      if (m.sticker_url) return el("img", { src: m.sticker_url, alt: t(`stickers.${m.sticker}`), loading: "lazy" });
      if (m.documento) {
        const d = m.documento;
        return el("a", { class: "tarjeta-documento", href: d.url, download: d.nombre },
          icono(t(`iconos_documento.${d.tipo}`)),
          el("span", {}, el("span", { class: "visually-hidden", text: `${t("chat.descargar")} ` }),
            el("span", { class: "nombre-documento", text: d.nombre }),
            el("span", { class: "tamano-documento", text: tamanoLegible(d.tamano_bytes) })));
      }
      return el("div", { class: "contenido-libre", text: m.texto });
    }

    function estado(m) {  // SRS v2.0: «Enviado» o «Visto» según el lastReadAt de la otra persona
      const visto = vistoHasta && new Date(vistoHasta) >= new Date(m.fecha_envio);
      return [icono(visto ? "bi-check2-all" : "bi-check2"), t(visto ? "chat.visto" : "chat.enviado")];
    }

    function actualizarEstados() {
      historial.querySelectorAll(".estado-mensaje").forEach((n) => n.replaceChildren(...estado({ fecha_envio: n.dataset.fecha })));
    }

    function fila(m) {
      if (vistos.has(m.id)) return null;
      vistos.add(m.id);
      if (!ultimo || m.fecha_envio > ultimo) ultimo = m.fecha_envio;
      const continua = anterior !== null && anterior.propio === m.es_propio;  // Gestalt: proximidad
      const meta = el("div", { class: "hora" }, formatoHora(m.fecha_envio));  // HH:MM en America/Lima (RN-34)
      if (m.es_propio) meta.append(t("separador"), el("span", { class: "estado-mensaje", "data-fecha": m.fecha_envio }, ...estado(m)));
      const clases = `${m.es_propio ? "propia" : "ajena"}${continua ? " continua" : ""}`;
      const burbuja = el("div", { class: `burbuja ${clases}${m.sticker_url ? " sticker" : ""}` }, contenido(m), meta);
      const nueva = el("div", { class: `fila-mensaje ${clases}` });
      if (!m.es_propio) {
        // La foto o el avatar va junto al último mensaje del grupo: se oculta en el anterior del mismo grupo
        if (continua) anterior.fila.querySelector(".avatar")?.classList.add("oculto");
        nueva.append(avatar(aparienciaOtra));
      }
      nueva.append(burbuja);
      anterior = { propio: m.es_propio, fila: nueva };
      return nueva;
    }

    function agregar(lista) {
      const cerca = historial.scrollHeight - historial.scrollTop - historial.clientHeight < 80;
      const nuevos = lista.map(fila).filter(Boolean);
      historial.append(...nuevos);
      if (nuevos.length && cerca) historial.scrollTop = historial.scrollHeight;
    }

    function recibir(r) {
      if (r.visto_hasta !== undefined) vistoHasta = r.visto_hasta;
      agregar(r.mensajes);
      actualizarEstados();
      mostrarAviso(r.aviso);
    }

    function mostrarAviso(a) {  // EA-04 / RF-CHT-14
      aviso.textContent = a && a.activo ? a.mensaje : "";
      aviso.classList.toggle("d-none", !(a && a.activo));
    }

    function marcarExpirado() {  // RF-CHT-25
      expirado = true;
      clearTimeout(temporizador);
      mostrarAviso(null);
      cerrarPaneles();
      alerta(mensajes, t("chat.expiro"), "secondary");
      formulario.querySelectorAll("textarea, input, button").forEach((n) => { n.disabled = true; });
      document.getElementById("reportar").classList.add("disabled");
    }

    async function sondear() {
      if (expirado) return;
      if (document.visibilityState === "visible") {
        try {
          const q = ultimo ? `?despues_de=${encodeURIComponent(ultimo)}` : "";
          recibir(await api(`/api/chats/${chatId}${q}`, { automatica: true }));
        } catch (error) {
          if (error.status === 410) { marcarExpirado(); return; }
        }
      }
      temporizador = setTimeout(sondear, 1000);  // RNF-REN-03: mensajes nuevos en ≤ 1 s
    }

    api(`/api/chats/${chatId}`).then((r) => {
      document.getElementById("contraparte").replaceChildren(autor(r.nickname_contraparte, r.apariencia_contraparte, { tamano: "md" }));
      document.getElementById("tipo").textContent = TIPOS[r.tipo_publicacion];
      document.getElementById("titulo").textContent = r.titulo_publicacion;
      aparienciaOtra = r.apariencia_contraparte;
      seccion.classList.remove("d-none");
      recibir(r);
      historial.scrollTop = historial.scrollHeight;
      temporizador = setTimeout(sondear, 1000);
    }).catch((error) => {
      if (error.status === 410) { seccion.classList.remove("d-none"); marcarExpirado(); }
      else if (error.status !== 401) alerta(mensajes, error.message);
    });

    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible" && !expirado) { clearTimeout(temporizador); sondear(); }
    });

    async function enviar(datos) {
      const m = await api(`/api/chats/${chatId}/mensajes`, { metodo: "POST", formulario: datos });
      limpiar(mensajes);
      agregar([m]);
      historial.scrollTop = historial.scrollHeight;
      mostrarAviso(null);  // el mensaje reinicia la expiración (RF-CHT-12)
    }

    /* El error de una imagen o un documento se muestra bajo la barra de adjuntos (no dentro del botón) y queda
     * enlazado a su <input> con aria-describedby (RNF-USA-03). */
    function errorDeAdjunto(error) {
      const datos = error.datos || {};
      const campos = [datos.campo, ...(datos.errores || []).map((e) => e.campo)];
      const campo = campos.find((c) => c === "imagen" || c === "documento");
      if (!campo) return false;
      limpiarErrores(formulario);
      const entrada = campo === "imagen" ? entradaImagen : entradaDocumento;
      adjuntoElegido.insertAdjacentElement("afterend", el("div", {
        class: "invalid-feedback d-block", id: `error-${campo}`, "data-error-de": campo, text: error.message }));
      entrada.setAttribute("aria-invalid", "true");
      entrada.setAttribute("aria-describedby", `ayuda-adjuntos error-${campo}`);
      entrada.focus();
      return true;
    }

    function manejarError(error) {
      if (error.status === 410) marcarExpirado();
      else if (error.status !== 401 && !errorDeAdjunto(error) && !mostrarErrores(formulario, error, { general: "texto" })) {
        alerta(mensajes, error.message);
      }
    }

    /* ---- Adjuntos: una imagen o un documento por mensaje; se ve cuál está elegido y se puede quitar ---- */
    function mostrarAdjunto() {
      adjuntoElegido.classList.toggle("d-none", !adjunto);
      if (!adjunto) { adjuntoElegido.replaceChildren(); return; }
      adjuntoElegido.replaceChildren(
        icono(adjunto.tipo === "imagen" ? "bi-image" : "bi-paperclip"),
        el("span", { text: t("chat.adjunto", { nombre: adjunto.archivo.name, tamano: tamanoLegible(adjunto.archivo.size) }) }),
        el("button", { type: "button", class: "btn btn-link btn-sm p-0", onclick: () => { adjunto = null; mostrarAdjunto(); texto.focus(); } },
          t("chat.quitar_adjunto")));
    }
    for (const [entrada, tipo] of [[entradaImagen, "imagen"], [entradaDocumento, "documento"]]) {
      entrada.addEventListener("change", () => {
        limpiarErrores(formulario);
        if (entrada.files.length) adjunto = { tipo, archivo: entrada.files[0] };
        entrada.value = "";
        mostrarAdjunto();
      });
    }

    async function datosDelFormulario() {
      const invalido = (detail) => new Banca.ErrorApi(422, { detail, errores: [{ campo: "texto", mensaje: detail }] });
      if (texto.value.trim() && adjunto) throw invalido(t("chat.un_contenido"));
      if (!texto.value.trim() && !adjunto) throw invalido(t("chat.vacio_v2"));
      const datos = new FormData();
      if (!adjunto) datos.append("texto", texto.value);
      else if (adjunto.tipo === "imagen") datos.append("imagen", await Banca.comprimirImagen(adjunto.archivo));
      else {
        if (adjunto.archivo.size > 10 * 1024 * 1024) throw invalido(t("chat.documento_grande"));
        datos.append("documento", adjunto.archivo);
      }
      return datos;
    }

    formulario.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      const boton = formulario.querySelector("[type=submit]");
      ocupado(boton, true);
      limpiarErrores(formulario);
      try {
        await enviar(await datosDelFormulario());
        texto.value = "";
        texto.dispatchEvent(new Event("input"));
        adjunto = null;
        mostrarAdjunto();
        cerrarPaneles();
        texto.focus();  // RNF-USA-08: se puede seguir escribiendo sin el ratón
      } catch (error) { manejarError(error); } finally { if (!expirado) ocupado(boton, false); }
    });

    /* ---- Emojis (Unicode, sin librerías) y stickers propios -------------------------------------------- */
    const EMOJIS = ["😀", "😁", "😂", "🙂", "😉", "😊", "😍", "🤔", "😮", "😢", "😴", "😎", "🙏", "👍", "👎", "👏",
                    "🙌", "💪", "👋", "🤝", "❤️", "🔥", "⭐", "🎉", "✅", "❌", "📚", "📝", "💻", "☕", "🍕", "⏰"];
    const STICKERS = Array.from({ length: 20 }, (_, i) => `sticker-${String(i + 1).padStart(2, "0")}`);
    const paneles = { emojis: document.getElementById("panel-emojis"), stickers: document.getElementById("panel-stickers") };
    const botones = { emojis: document.getElementById("boton-emojis"), stickers: document.getElementById("boton-stickers") };

    function cerrarPaneles(devolverFoco = null) {
      for (const nombre of Object.keys(paneles)) {
        paneles[nombre].hidden = true;
        botones[nombre].setAttribute("aria-expanded", "false");
      }
      if (devolverFoco) botones[devolverFoco].focus();
    }
    function alternar(nombre) {
      const abrir = paneles[nombre].hidden;
      cerrarPaneles();
      if (!abrir) return;
      if (!paneles[nombre].childElementCount) llenar(nombre);
      paneles[nombre].hidden = false;
      botones[nombre].setAttribute("aria-expanded", "true");
      paneles[nombre].querySelector("button").focus();
    }
    function insertarEmoji(emoji) {
      const inicio = texto.selectionStart ?? texto.value.length, fin = texto.selectionEnd ?? texto.value.length;
      if (texto.value.length - (fin - inicio) + emoji.length > 500) return;
      texto.setRangeText(emoji, inicio, fin, "end");
      texto.dispatchEvent(new Event("input"));
    }
    function llenar(nombre) {
      if (nombre === "emojis") {
        paneles.emojis.replaceChildren(...EMOJIS.map((e) => el("button", { type: "button", text: e, onclick: () => insertarEmoji(e) })));
      } else {
        paneles.stickers.replaceChildren(...STICKERS.map((s) => el("button", {
          type: "button", title: t(`stickers.${s}`),
          onclick: async (evento) => {
            const boton = evento.currentTarget;
            const datos = new FormData();
            datos.append("sticker", s);
            ocupado(boton, true);
            try { await enviar(datos); cerrarPaneles("stickers"); } catch (error) { manejarError(error); } finally { ocupado(boton, false); }
          } }, el("img", { src: `/static/stickers/${s}.svg`, alt: t(`stickers.${s}`), loading: "lazy" }))));
      }
    }
    for (const nombre of Object.keys(paneles)) {
      botones[nombre].addEventListener("click", () => alternar(nombre));
      paneles[nombre].addEventListener("keydown", (evento) => {
        if (evento.key.toLowerCase() === "escape") { evento.preventDefault(); cerrarPaneles(nombre); }
      });
    }
  }
})();
