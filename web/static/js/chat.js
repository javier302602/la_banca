/* M04 — Chat: responder (CU-10), enviar mensaje (CU-11), mis chats y chat abierto (CU-12, EA-04).
 * El sondeo de 1 s solo corre en la página de un chat abierto y visible. */
"use strict";

(() => {
  const { api, alerta, limpiar, el, contador, ocupado, mostrarErrores, limpiarErrores, TIPOS, t, formatoHora, etiquetaTipo } = Banca;
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
      document.getElementById("contexto-autor").textContent = p.nickname_autor;
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
      el("div", {},
        el("div", { class: "fw-semibold", text: c.nickname_contraparte }),
        el("div", { class: "small text-body-secondary", text: `${TIPOS[c.tipo_publicacion]}${t("separador")}${c.titulo_publicacion}` })),
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
    const vistos = new Set();
    let ultimo = null, temporizador = null, expirado = false, ladoAnterior = null;
    contador(document.getElementById("texto"), document.getElementById("contador-texto"), 500);

    function burbuja(m) {
      if (vistos.has(m.id)) return null;
      vistos.add(m.id);
      if (!ultimo || m.fecha_envio > ultimo) ultimo = m.fecha_envio;
      const continua = ladoAnterior === m.es_propio;  // Gestalt: mensajes seguidos del mismo autor se agrupan
      ladoAnterior = m.es_propio;
      const contenido = m.imagen_url
        ? el("img", { src: m.imagen_url, alt: t("imagen.alt", { nickname: m.nickname_emisor }), loading: "lazy" })
        : el("div", { class: "contenido-libre", text: m.texto });
      return el("div", { class: `burbuja ${m.es_propio ? "propia" : "ajena"}${continua ? " continua" : ""}` }, contenido,
        el("div", { class: "hora", text: formatoHora(m.fecha_envio) }));  // HH:MM en America/Lima, calculada en el servidor (RN-34)
    }

    function agregar(lista) {
      const cerca = historial.scrollHeight - historial.scrollTop - historial.clientHeight < 80;
      const nuevos = lista.map(burbuja).filter(Boolean);
      historial.append(...nuevos);
      if (nuevos.length && cerca) historial.scrollTop = historial.scrollHeight;
    }

    function mostrarAviso(a) {  // EA-04 / RF-CHT-14
      aviso.textContent = a && a.activo ? a.mensaje : "";
      aviso.classList.toggle("d-none", !(a && a.activo));
    }

    function marcarExpirado() {  // RF-CHT-25
      expirado = true;
      clearTimeout(temporizador);
      mostrarAviso(null);
      alerta(mensajes, t("chat.expiro"), "secondary");
      formulario.querySelectorAll("textarea, input, button").forEach((n) => { n.disabled = true; });
      document.getElementById("reportar").classList.add("disabled");
    }

    async function sondear() {
      if (expirado) return;
      if (document.visibilityState === "visible") {
        try {
          const q = ultimo ? `?despues_de=${encodeURIComponent(ultimo)}` : "";
          const r = await api(`/api/chats/${chatId}${q}`, { automatica: true });
          agregar(r.mensajes);
          mostrarAviso(r.aviso);
        } catch (error) {
          if (error.status === 410) { marcarExpirado(); return; }
        }
      }
      temporizador = setTimeout(sondear, 1000);  // RNF-REN-03: mensajes nuevos en ≤ 1 s
    }

    api(`/api/chats/${chatId}`).then((r) => {
      document.getElementById("contraparte").textContent = r.nickname_contraparte;
      document.getElementById("tipo").textContent = TIPOS[r.tipo_publicacion];
      document.getElementById("titulo").textContent = r.titulo_publicacion;
      seccion.classList.remove("d-none");
      agregar(r.mensajes);
      historial.scrollTop = historial.scrollHeight;
      mostrarAviso(r.aviso);
      temporizador = setTimeout(sondear, 1000);
    }).catch((error) => {
      if (error.status === 410) { seccion.classList.remove("d-none"); marcarExpirado(); }
      else if (error.status !== 401) alerta(mensajes, error.message);
    });

    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible" && !expirado) { clearTimeout(temporizador); sondear(); }
    });

    formulario.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      const boton = formulario.querySelector("[type=submit]");
      ocupado(boton, true);
      limpiarErrores(formulario);
      try {
        const m = await api(`/api/chats/${chatId}/mensajes`, { metodo: "POST", formulario: await datosMensaje() });
        formulario.reset();
        document.getElementById("texto").dispatchEvent(new Event("input"));
        limpiar(mensajes);
        agregar([m]);
        historial.scrollTop = historial.scrollHeight;
        mostrarAviso(null);  // el mensaje reinicia la expiración (RF-CHT-12)
        document.getElementById("texto").focus();  // RNF-USA-08: se puede seguir escribiendo sin el ratón
      } catch (error) {
        if (error.status === 410) marcarExpirado();
        else if (error.status !== 401 && !mostrarErrores(formulario, error, { general: "texto" })) alerta(mensajes, error.message);
      } finally { if (!expirado) ocupado(boton, false); }
    });
  }
})();
