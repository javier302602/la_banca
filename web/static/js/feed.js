/* M03 — Feed «Ahora» (CU-08) y detalle de publicación (CU-09). */
"use strict";

(() => {
  const { api, alerta, limpiar, el, restante, refrescarRestantes, TIPOS } = Banca;
  const pagina = document.body.dataset.pagina;
  const mensajes = document.getElementById("mensajes");

  if (pagina === "feed") {
    const lista = document.getElementById("lista");
    const vacio = document.getElementById("vacio");
    const centinela = document.getElementById("centinela");
    const filtro = document.getElementById("filtro-tipo");
    const quitarFiltro = document.getElementById("quitar-filtro");
    let siguiente = null, bloquesCargados = 0, cargando = false;

    const tarjeta = (p) => el("div", { class: "col-md-6 col-lg-4" },
      el("a", { class: `card h-100 text-decoration-none text-body tarjeta-publicacion tipo-${p.tipo}`,
                href: `/publicaciones/${encodeURIComponent(p.id)}` },
        el("div", { class: "card-body" },
          el("div", { class: "d-flex gap-2 mb-2" },
            el("span", { class: "badge etiqueta-tipo", text: TIPOS[p.tipo] }),
            p.es_propia ? el("span", { class: "badge etiqueta-propia", text: "Tu publicación" }) : null),
          el("h2", { class: "h6 card-title", text: p.titulo }),
          el("p", { class: "small text-body-secondary mb-0" }, el("span", { text: p.nickname_autor }), " · ",
            el("span", { "data-expira": p.fecha_expiracion, text: restante(p.fecha_expiracion) })))));

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
        vacio.textContent = ultima.mensaje_vacio || "";
        vacio.classList.toggle("d-none", !ultima.mensaje_vacio);
        centinela.textContent = siguiente ? "Cargando más…" : "";
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
        centinela.textContent = siguiente ? "Cargando más…" : "";
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

    api(`/api/publicaciones/${enlaceId}`).then((p) => {
      const tipo = document.getElementById("tipo");
      tipo.textContent = TIPOS[p.tipo];
      tipo.classList.add(`tipo-${p.tipo}`);  // Gestalt: mismo color que en el feed (similitud)
      document.getElementById("titulo").textContent = p.titulo;
      document.getElementById("descripcion").textContent = p.descripcion;
      document.getElementById("autor").textContent = p.nickname_autor;
      const r = document.getElementById("restante");
      r.dataset.expira = p.fecha_expiracion;
      r.textContent = restante(p.fecha_expiracion);
      document.getElementById("propia").classList.toggle("d-none", !p.es_propia);
      if (p.puede_responder) acciones.append(el("a", { class: "btn btn-primary", href: `/publicaciones/${enlaceId}/responder`, text: "Responder" }));
      if (p.chat_existente_id) acciones.append(el("a", { class: "btn btn-primary", href: `/chats/${encodeURIComponent(p.chat_existente_id)}`, text: "Abrir chat" }));
      if (p.puede_reportar) acciones.append(el("a", { class: "btn btn-outline-danger", href: `/publicaciones/${enlaceId}/reportar`, text: "Reportar" }));
      tarjeta.classList.remove("d-none");
    }).catch((error) => {
      if (error.status !== 401) alerta(mensajes, error.message, error.status === 410 ? "secondary" : "danger");  // RF-FED-10
    });
    setInterval(() => refrescarRestantes(tarjeta), 30000);
  }
})();
