/* M02 — Publicaciones: crear (CU-05), ver mis activas (CU-06) y cerrar (CU-07). */
"use strict";

(() => {
  const { api, alerta, el, limpiar, contador, ocupado, restante, refrescarRestantes, mostrarErrores, limpiarErrores,
          errorEnCampo, TIPOS } = Banca;
  const pagina = document.body.dataset.pagina;
  const mensajes = document.getElementById("mensajes");

  if (pagina === "crear-publicacion") {
    const formulario = document.getElementById("form-publicacion");
    const cupo = document.getElementById("cupo");
    contador(document.getElementById("titulo"), document.getElementById("contador-titulo"), 80);
    contador(document.getElementById("descripcion"), document.getElementById("contador-descripcion"), 500);

    const avisoCupo = document.getElementById("aviso-cupo");
    const cargarCupo = async () => {  // RF-PUB-13
      try {
        const c = await api("/api/publicaciones/cupo");
        cupo.textContent = `Publicaciones activas: ${c.activas} de ${c.maximo}`;
        // Nielsen H5 (prevenir errores): sin cupo, se avisa antes de escribir y no se permite enviar
        const lleno = c.activas >= c.maximo;
        avisoCupo.replaceChildren(...(lleno ? [
          el("span", { text: `Ya tienes ${c.maximo} publicaciones activas, el máximo permitido. Cierra una o espera a que expire. ` }),
          el("a", { class: "alert-link", href: "/publicaciones/mias", text: "Ir a Mis publicaciones" })] : []));
        avisoCupo.classList.toggle("d-none", !lleno);
        formulario.querySelector("[type=submit]").disabled = lleno;
      } catch (e) { /* informativo */ }
    };
    cargarCupo();

    formulario.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      const boton = formulario.querySelector("[type=submit]");
      const tipo = formulario.querySelector("input[name=tipo]:checked");
      limpiarErrores(formulario);
      if (!tipo) {  // RNF-USA-03: junto al grupo de tipos
        errorEnCampo(formulario, "tipo", "Selecciona el tipo de publicación").focus();
        return;
      }
      ocupado(boton, true);
      try {
        const p = await api("/api/publicaciones", { metodo: "POST", cuerpo: {
          tipo: tipo.value, titulo: document.getElementById("titulo").value,
          descripcion: document.getElementById("descripcion").value } });
        location.href = `/publicaciones/${encodeURIComponent(p.id)}`;
      } catch (error) {
        if (mostrarErrores(formulario, error)) limpiar(mensajes); else alerta(mensajes, error.message);
        cargarCupo();
      } finally { ocupado(boton, false); }
    });
  }

  if (pagina === "mis-publicaciones") {
    const lista = document.getElementById("lista");
    const vacio = document.getElementById("vacio");

    const fila = (p) => el("li", { class: "list-group-item d-flex justify-content-between align-items-center gap-2" },
      el("div", {},
        el("span", { class: `badge etiqueta-tipo tipo-${p.tipo} me-2`, text: TIPOS[p.tipo] }),
        el("a", { href: `/publicaciones/${encodeURIComponent(p.id)}`, text: p.titulo }),
        el("div", { class: "small text-body-secondary" }, "Tiempo restante: ",
          el("span", { "data-expira": p.fecha_expiracion, text: restante(p.fecha_expiracion) }))),
      el("button", { class: "btn btn-outline-danger btn-sm", type: "button", text: "Cerrar",
                     onclick: (e) => cerrar(p, e.currentTarget) }));

    async function cargar() {
      try {
        const r = await api("/api/publicaciones/mias");
        lista.replaceChildren(...r.items.map(fila));
        vacio.classList.toggle("d-none", r.items.length > 0);
      } catch (error) { if (error.status !== 401) alerta(mensajes, error.message); }
    }

    async function cerrar(p, boton) {  // RF-PUB-08: confirmación previa
      if (!confirm("¿Cerrar esta publicación? No podrás reactivarla")) return;
      ocupado(boton, true);
      try {
        await api(`/api/publicaciones/${encodeURIComponent(p.id)}/cerrar`, { metodo: "POST" });
        alerta(mensajes, "Publicación cerrada", "success");
      } catch (error) { alerta(mensajes, error.message); }
      cargar();
    }

    cargar();
    setInterval(() => refrescarRestantes(lista), 30000);
  }
})();
