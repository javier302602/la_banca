/* M09 — Panel de administradores (Fase 5): reportes de publicaciones, chats y videollamadas, acciones e
 * historial. Todo pasa por /api/admin/* (el servidor exige que el correo esté en ADMIN_EMAILS). */
"use strict";

(() => {
  if (document.body.dataset.pagina !== "admin") return;
  const { api, alerta, limpiar, el, t, icono, formatoFecha, formatoHora } = Banca;
  const $ = (id) => document.getElementById(id);
  const mensajes = $("mensajes");
  const lista = $("lista-reportes");
  const filtro = $("filtro-estado");
  const dialogo = $("dialogo-accion");
  let pendiente = null;  // { reporte, accion } que se confirma en el diálogo

  const fecha = (iso) => `${formatoFecha(iso)} ${formatoHora(iso)}`;
  const persona = (p) => (p ? `@${p.nickname}${p.nombre ? ` — ${p.nombre}` : ""}${p.carrera ? ` (${p.carrera})` : ""}` : "—");

  /* ---- Contenido guardado al reportar (copia; el original pudo cambiar o borrarse) ------------------------ */
  function contenido(r) {
    if (r.tipo === "VIDEOLLAMADA") {
      const sala = r.contenido.sala;
      return el("p", { class: "small text-body-secondary mb-0" }, icono("bi-camera-video-off"),
        ` ${t("admin.sin_video")}`, sala ? ` ${t("admin.sala", { inicio: fecha(sala.inicio), fin: sala.fin ? fecha(sala.fin) : "—" })}` : "");
    }
    const partes = [];
    const pub = r.contenido.publicacion;
    if (pub && r.tipo === "PUBLICACION") {
      partes.push(el("p", { class: "mb-1" }, el("strong", { text: pub.title })),
                  el("p", { class: "contenido-libre small", text: pub.description || "" }));
    } else if (pub) {
      partes.push(el("p", { class: "small text-body-secondary", text: t("admin.chat_de", { titulo: pub.title }) }));
    }
    if (r.tipo === "PUBLICACION" && r.imagenes.length) {
      partes.push(el("div", { class: "d-flex flex-wrap gap-2" },
        ...r.imagenes.map((url) => el("img", { class: "miniatura-admin", src: url, alt: t("admin.imagen_reportada") }))));
    }
    if (r.contenido.mensajes.length) {
      partes.push(el("ol", { class: "mensajes-admin" }, ...r.contenido.mensajes.map((m) => {
        const cuerpo = [];
        if (m.text) cuerpo.push(el("span", { class: "contenido-libre", text: m.text }));
        if (m.imageKey && r.archivos[m.imageKey]) cuerpo.push(el("img", { class: "miniatura-admin", src: r.archivos[m.imageKey], alt: t("admin.imagen_reportada") }));
        if (m.sticker) cuerpo.push(el("span", { text: `[${m.sticker}]` }));
        if (m.document && r.archivos[m.document.key]) cuerpo.push(el("a", { href: r.archivos[m.document.key], download: m.document.fileName, text: m.document.fileName }));
        return el("li", {}, el("strong", { text: `@${m.senderNickname}: ` }), ...cuerpo);
      })));
    }
    return el("div", { class: "contenido-reportado" }, ...partes);
  }

  /* ---- Tarjeta de un reporte con sus acciones ------------------------------------------------------------- */
  function tarjeta(r) {
    const motivo = t(`admin.motivos.${r.motivo}`);
    const acciones = el("div", { class: "d-flex flex-wrap gap-2 mt-3" });
    const boton = (accion, clase) => el("button", { type: "button", class: `btn btn-sm ${clase}`, text: t(`admin.acciones.${accion}`),
                                                    onclick: () => abrir(r, accion) });
    if (r.tipo !== "VIDEOLLAMADA") acciones.append(boton("ELIMINAR_CONTENIDO", "btn-outline-danger"));
    acciones.append(boton("ADVERTIR", "btn-outline-secondary"), boton("SUSPENDER", "btn-outline-danger"),
                    boton("BANEAR", "btn-danger"));
    if (r.estado === "PENDIENTE") acciones.append(boton("DESCARTAR", "btn-outline-secondary"));
    return el("article", { class: "card tarjeta-reporte", "data-estado": r.estado },
      el("div", { class: "card-body" },
        el("div", { class: "d-flex flex-wrap gap-2 align-items-center mb-2" },
          el("span", { class: "badge etiqueta-tipo", text: t(`admin.tipos.${r.tipo}`) }),
          el("span", { class: `badge estado-reporte estado-${r.estado}`, text: t(`admin.estados.${r.estado}`) }),
          r.automatico ? el("span", { class: "badge etiqueta-propia" }, icono("bi-robot"), ` ${t("admin.automatico")}`) : null,
          el("span", { class: "small text-body-secondary ms-auto", text: fecha(r.fecha) })),
        el("h2", { class: "h6 mb-2", text: motivo }),
        el("dl", { class: "datos-reporte" },
          el("dt", { text: t("admin.reporto") }), el("dd", { text: r.automatico ? t("admin.filtro") : persona(r.reportante) }),
          el("dt", { text: t("admin.reportado") }), el("dd", { text: persona(r.reportado) }),
          r.detalle ? el("dt", { text: t("admin.detalle") }) : null, r.detalle ? el("dd", { class: "contenido-libre", text: r.detalle }) : null),
        contenido(r),
        r.acciones.length ? el("ul", { class: "small text-body-secondary mt-2 mb-0" }, ...r.acciones.map((a) =>
          el("li", { text: `${fecha(a.at)} · ${t(`admin.acciones.${a.action}`)}${a.detail ? ` · ${a.detail}` : ""}` }))) : null,
        acciones));
  }

  async function cargar() {
    const estado = filtro.value;
    try {
      const r = await api(estado === "TODOS" ? "/api/admin/reportes?todos=true" : `/api/admin/reportes?estado=${estado}`);
      lista.replaceChildren(...r.reportes.map(tarjeta));
      $("sin-reportes").classList.toggle("d-none", r.reportes.length > 0);
      $("total-pendientes").textContent = r.pendientes || "";
    } catch (error) { if (error.status !== 401) alerta(mensajes, error.message); }
  }

  /* ---- Confirmación de una acción ------------------------------------------------------------------------ */
  function abrir(reporte, accion) {
    pendiente = { reporte, accion };
    $("titulo-accion").textContent = t(`admin.acciones.${accion}`);
    $("texto-accion").textContent = t(`admin.confirmaciones.${accion}`, { nickname: reporte.reportado ? reporte.reportado.nickname : "—" });
    $("campo-dias").hidden = accion !== "SUSPENDER";
    $("campo-mensaje").hidden = accion !== "ADVERTIR";
    $("mensaje-accion").value = "";
    dialogo.showModal();
  }

  $("cancelar-accion").addEventListener("click", () => dialogo.close());
  $("form-accion").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const { reporte, accion } = pendiente;
    const cuerpo = { accion };
    if (accion === "SUSPENDER") cuerpo.dias = Number($("dias").value);
    if (accion === "ADVERTIR") cuerpo.mensaje = $("mensaje-accion").value;
    try {
      await api(`/api/admin/reportes/${reporte.origen}/${encodeURIComponent(reporte.id)}/acciones`, { metodo: "POST", cuerpo });
      dialogo.close();
      alerta(mensajes, t("admin.hecho"), "success");
      await cargar();
    } catch (error) {
      dialogo.close();
      if (error.status !== 401) alerta(mensajes, error.message);
    }
  });

  /* ---- Historial ------------------------------------------------------------------------------------------ */
  async function cargarHistorial() {
    try {
      const r = await api("/api/admin/historial");
      $("filas-historial").replaceChildren(...r.acciones.map((a) => el("tr", {},
        el("td", { text: fecha(a.fecha) }), el("td", { text: `@${a.admin}` }), el("td", { text: t(`admin.acciones.${a.accion}`) }),
        el("td", { text: `@${a.usuario}` }), el("td", { text: a.tipo_reporte ? t(`admin.tipos.${a.tipo_reporte}`) : "" }),
        el("td", { class: "contenido-libre", text: a.detalle }))));
    } catch (error) { if (error.status !== 401) alerta(mensajes, error.message); }
  }

  function mostrar(seccion) {
    const historial = seccion === "historial";
    $("seccion-historial").hidden = !historial;
    $("seccion-reportes").hidden = historial;
    $("filtros-reportes").hidden = historial;
    for (const [id, activa] of [["tab-reportes", !historial], ["tab-historial", historial]]) {
      $(id).setAttribute("aria-selected", String(activa));
      $(id).classList.toggle("btn-primary", activa);
      $(id).classList.toggle("btn-outline-secondary", !activa);
    }
    limpiar(mensajes);
    if (historial) cargarHistorial(); else cargar();
  }

  $("tab-reportes").addEventListener("click", () => mostrar("reportes"));
  $("tab-historial").addEventListener("click", () => mostrar("historial"));
  filtro.addEventListener("change", cargar);
  cargar();
})();
