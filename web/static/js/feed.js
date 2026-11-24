/* M03 — Feed «Ahora» (CU-08) y detalle de publicación (CU-09). */
"use strict";

(() => {
  const { api, alerta, limpiar, el, restante, refrescarRestantes, TIPOS, t, icono, etiquetaTipo, autor, barraReacciones } = Banca;
  const pagina = document.body.dataset.pagina;
  const mensajes = document.getElementById("mensajes");

  if (pagina === "feed") {
    const lista = document.getElementById("lista");
    const vacio = document.getElementById("vacio");
    const centinela = document.getElementById("centinela");
    const filtro = document.getElementById("filtro-tipo");
    const quitarFiltro = document.getElementById("quitar-filtro");
    let siguiente = null, bloquesCargados = 0, cargando = false;

    /* Tarjeta: medio (imagen o video) → tipo y caducidad → título y extracto → autor → reacciones.
     * El enlace al detalle va en el medio y en el título; las reacciones quedan fuera del enlace. */
    const medio = (p, href) => {
      if (p.miniatura) {
        return el("a", { class: "medio-publicacion", href, tabindex: "-1", "aria-hidden": "true" },
          el("img", { src: p.miniatura, loading: "lazy", alt: "" }),
          p.video ? el("span", { class: "marca-video" }, icono("bi-play-fill")) : null);
      }
      if (p.video) {
        return el("div", { class: "medio-publicacion" },
          el("video", { src: p.video, controls: true, preload: "metadata", playsinline: true,
                        "aria-label": t("galeria.video_de", { titulo: p.titulo }) }));
      }
      return null;
    };

    const tarjeta = (p) => {
      const href = `/publicaciones/${encodeURIComponent(p.id)}`;
      return el("article", { class: `card h-100 tarjeta-publicacion tipo-${p.tipo}` },
        medio(p, href),
        el("div", { class: "card-body" },
          el("div", { class: "d-flex flex-wrap align-items-center gap-2" },
            el("span", { class: "badge etiqueta-tipo" }, ...etiquetaTipo(p.tipo)),
            p.es_propia ? el("span", { class: "badge etiqueta-propia", text: t("feed.tu_publicacion") }) : null,
            el("span", { class: "chip-expira ms-auto" }, icono("bi-clock"), ` ${t("feed.expira_en")} `,
              el("span", { "data-expira": p.fecha_expiracion, text: restante(p.fecha_expiracion) }))),
          el("h2", { class: "h6 card-title" }, el("a", { href, class: "enlace-titulo", text: p.titulo })),
          p.extracto ? el("p", { class: "extracto text-body-secondary", text: p.extracto }) : null,
          el("p", { class: "small text-body-secondary d-flex align-items-center flex-wrap gap-2" },
            autor(p.nickname_autor, p.apariencia_autor, { enlace: false }),
            p.num_imagenes ? el("span", {}, icono("bi-images"),
              ` ${p.num_imagenes === 1 ? t("galeria.una_imagen") : t("galeria.num_imagenes", { n: p.num_imagenes })}`) : null,
            p.video ? el("span", {}, icono("bi-camera-video"), ` ${t("galeria.con_video")}`) : null)),
        el("div", { class: "card-footer" }, barraReacciones(p.id, p.reacciones)));
    };

    const url = (cursor) => {
      const q = new URLSearchParams();
      if (filtro.value) q.set("tipo", filtro.value);  // RF-FED-17: el filtro se mantiene al actualizar
      if (cursor) q.set("cursor", cursor);
      return `/api/feed?${q}`;
    };

    async function cargarDesdeCero({ automatica = false } = {}) {  // RF-FED-08 / RF-FED-11
      if (cargando) return;
      cargando = true;
      const bloques = Math.max(1, bloquesCargados);
      try {
        let items = [], cursor = null, ultima = null;
        for (let i = 0; i < bloques; i++) {
          ultima = await api(url(cursor), { automatica });
          items = items.concat(ultima.items);
          cursor = ultima.siguiente_cursor;
          if (!cursor) break;
        }
        siguiente = cursor;
        bloquesCargados = Math.ceil(items.length / ultima.tamano_bloque) || 1;
        lista.replaceChildren(...items.map(tarjeta));
        document.getElementById("vacio-texto").textContent = ultima.mensaje_vacio || "";
        vacio.classList.toggle("d-none", !ultima.mensaje_vacio);
        centinela.textContent = siguiente ? t("feed.cargando_mas") : "";
        limpiar(mensajes);
      } catch (error) { if (error.status !== 401) alerta(mensajes, error.message); }
      finally { cargando = false; }
    }

    async function cargarSiguiente() {  // RF-FED-19
      if (cargando || !siguiente) return;
      cargando = true;
      try {
        const r = await api(url(siguiente));
        lista.append(...r.items.map(tarjeta));
        siguiente = r.siguiente_cursor;
        bloquesCargados += 1;
        centinela.textContent = siguiente ? t("feed.cargando_mas") : "";
      } catch (error) { if (error.status !== 401) alerta(mensajes, error.message); }
      finally { cargando = false; }
    }

    filtro.addEventListener("change", () => {
      quitarFiltro.classList.toggle("d-none", !filtro.value);
      bloquesCargados = 0;
      cargarDesdeCero();
    });
    quitarFiltro.addEventListener("click", () => {  // RF-FED-16
      filtro.value = "";
      filtro.dispatchEvent(new Event("change"));
    });
    document.getElementById("actualizar").addEventListener("click", () => cargarDesdeCero());

    new IntersectionObserver((entradas) => {
      if (entradas.some((e) => e.isIntersecting)) cargarSiguiente();
    }, { rootMargin: "200px" }).observe(centinela);

    cargarDesdeCero();
    setInterval(() => { if (document.visibilityState === "visible") cargarDesdeCero({ automatica: true }); }, 60000);
    setInterval(() => refrescarRestantes(lista), 30000);
  }

  if (pagina === "detalle") {
    const id = document.getElementById("publicacion").dataset.id;
    const tarjeta = document.getElementById("detalle");
    const acciones = document.getElementById("acciones");
    const enlaceId = encodeURIComponent(id);

    /* Galería (SRS v2.0): imagen grande y miniaturas; la miniatura activa lleva aria-current. */
    function mostrarGaleria(p) {
      if (!p.imagenes || !p.imagenes.length) return;
      const total = p.imagenes.length;
      const grande = document.getElementById("galeria-imagen");
      const miniaturas = document.getElementById("galeria-miniaturas");
      const ver = (i) => {
        grande.src = p.imagenes[i];
        grande.alt = t("galeria.alt", { n: i + 1, total, titulo: p.titulo });
        miniaturas.querySelectorAll("button").forEach((b, j) => b.setAttribute("aria-current", String(i === j)));
      };
      if (total > 1) {
        miniaturas.replaceChildren(...p.imagenes.map((url, i) => el("button", {
          type: "button", "aria-label": t("galeria.miniatura", { n: i + 1, total }), onclick: () => ver(i) },
          el("img", { src: url, alt: "", loading: "lazy" }))));
      }
      ver(0);
      document.getElementById("galeria").hidden = false;
    }

    api(`/api/publicaciones/${enlaceId}`).then((p) => {
      const tipo = document.getElementById("tipo");
      tipo.replaceChildren(...etiquetaTipo(p.tipo));
      tipo.classList.add(`tipo-${p.tipo}`);  // Gestalt: mismo color que en el feed (similitud)
      document.getElementById("titulo").textContent = p.titulo;
      document.getElementById("descripcion").textContent = p.descripcion;
      mostrarGaleria(p);
      if (p.video) {
        const video = document.getElementById("video");
        video.src = p.video;
        video.setAttribute("aria-label", t("galeria.video_de", { titulo: p.titulo }));
        video.hidden = false;
      }
      document.getElementById("reacciones").replaceChildren(barraReacciones(p.id, p.reacciones));
      document.getElementById("autor").replaceChildren(autor(p.nickname_autor, p.apariencia_autor));  // enlace al perfil
      const r = document.getElementById("restante");
      r.dataset.expira = p.fecha_expiracion;
      r.textContent = restante(p.fecha_expiracion);
      document.getElementById("propia").classList.toggle("d-none", !p.es_propia);
      if (p.puede_responder) acciones.append(el("a", { class: "btn btn-primary", href: `/publicaciones/${enlaceId}/responder` }, icono("bi-reply"), ` ${t("feed.responder")}`));
      if (p.chat_existente_id) acciones.append(el("a", { class: "btn btn-primary", href: `/chats/${encodeURIComponent(p.chat_existente_id)}` }, icono("bi-chat-text"), ` ${t("feed.abrir_chat")}`));
      if (p.puede_reportar) acciones.append(el("a", { class: "btn btn-outline-danger", href: `/publicaciones/${enlaceId}/reportar` }, icono("bi-flag"), ` ${t("feed.reportar")}`));
      tarjeta.classList.remove("d-none");
    }).catch((error) => {
      if (error.status !== 401) alerta(mensajes, error.message, error.status === 410 ? "secondary" : "danger");  // RF-FED-10
    });
    setInterval(() => refrescarRestantes(tarjeta), 30000);
  }
})();
