/* M02 — Publicaciones: crear (CU-05), ver mis activas (CU-06) y cerrar (CU-07). */
"use strict";

(() => {
  const { api, alerta, el, limpiar, contador, ocupado, restante, refrescarRestantes, mostrarErrores, limpiarErrores,
          errorEnCampo, TIPOS, t, icono, etiquetaTipo, comprimirImagen } = Banca;
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
        cupo.textContent = t("publicaciones.cupo", c);
        // Nielsen H5 (prevenir errores): sin cupo, se avisa antes de escribir y no se permite enviar
        const lleno = c.activas >= c.maximo;
        avisoCupo.replaceChildren(...(lleno ? [
          el("span", { text: `${t("publicaciones.cupo_lleno", c)} ` }),
          el("a", { class: "alert-link", href: "/publicaciones/mias", text: t("publicaciones.ir_a_mias") })] : []));
        avisoCupo.classList.toggle("d-none", !lleno);
        formulario.querySelector("[type=submit]").disabled = lleno;
      } catch (e) { /* informativo */ }
    };
    cargarCupo();

    /* Imágenes (SRS v2.0): hasta 3; se ven antes de publicar y cada una se puede quitar. El <input> real se
     * vacía y la lista elegida vive en `elegidas`, así quitar una no obliga a elegir todas de nuevo. */
    const MAX_IMAGENES = 3;
    const entrada = document.getElementById("imagenes");
    const vista = document.getElementById("vista-previa");
    const nombre = document.getElementById("nombre-imagenes");
    let elegidas = [];
    const urls = new Map();
    const pintarVista = () => {
      urls.forEach((url, archivo) => { if (!elegidas.includes(archivo)) { URL.revokeObjectURL(url); urls.delete(archivo); } });
      vista.replaceChildren(...elegidas.map((archivo) => {
        if (!urls.has(archivo)) urls.set(archivo, URL.createObjectURL(archivo));
        return el("li", {}, el("img", { src: urls.get(archivo), alt: archivo.name }),
          el("button", { type: "button", class: "btn btn-danger btn-sm", "aria-label": t("publicaciones.quitar_imagen", { nombre: archivo.name }),
                         onclick: () => { elegidas = elegidas.filter((a) => a !== archivo); pintarVista(); entrada.focus(); } },
             icono("bi-x")));
      }));
      nombre.textContent = elegidas.length ? t("publicaciones.imagenes_elegidas", { n: elegidas.length }) : t("publicaciones.ninguna_imagen");
    };
    entrada.addEventListener("change", (evento) => {
      evento.stopImmediatePropagation();  // el nombre lo pinta pintarVista, no el selector genérico
      limpiarErrores(formulario);
      const nuevas = Array.from(entrada.files);
      if (elegidas.length + nuevas.length > MAX_IMAGENES) {
        errorEnCampo(formulario, "imagenes", t("publicaciones.demasiadas_imagenes"));
      }
      elegidas = elegidas.concat(nuevas).slice(0, MAX_IMAGENES);
      entrada.value = "";
      pintarVista();
    }, true);

    formulario.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      const boton = formulario.querySelector("[type=submit]");
      const tipo = formulario.querySelector("input[name=tipo]:checked");
      limpiarErrores(formulario);
      if (!tipo) {  // RNF-USA-03: junto al grupo de tipos
        errorEnCampo(formulario, "tipo", t("publicaciones.selecciona_tipo")).focus();
        return;
      }
      ocupado(boton, true);
      try {
        const campos = { tipo: tipo.value, titulo: document.getElementById("titulo").value,
                         descripcion: document.getElementById("descripcion").value };
        let p;
        if (elegidas.length) {  // multipart; cada imagen se comprime en el navegador si supera 4 MB
          const datos = new FormData();
          Object.entries(campos).forEach(([clave, valor]) => datos.append(clave, valor));
          for (const archivo of elegidas) datos.append("imagenes", await comprimirImagen(archivo));
          p = await api("/api/publicaciones", { metodo: "POST", formulario: datos });
        } else {
          p = await api("/api/publicaciones", { metodo: "POST", cuerpo: campos });
        }
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
        el("span", { class: `badge etiqueta-tipo tipo-${p.tipo} me-2` }, ...etiquetaTipo(p.tipo)),
        el("a", { href: `/publicaciones/${encodeURIComponent(p.id)}`, text: p.titulo }),
        el("div", { class: "small text-body-secondary" }, t("publicaciones.tiempo_restante"),
          el("span", { "data-expira": p.fecha_expiracion, text: restante(p.fecha_expiracion) }))),
      el("button", { class: "btn btn-outline-danger btn-sm", type: "button", text: t("publicaciones.cerrar"),
                     onclick: (e) => cerrar(p, e.currentTarget) }));

    async function cargar() {
      try {
        const r = await api("/api/publicaciones/mias");
        lista.replaceChildren(...r.items.map(fila));
        vacio.classList.toggle("d-none", r.items.length > 0);
      } catch (error) { if (error.status !== 401) alerta(mensajes, error.message); }
    }

    async function cerrar(p, boton) {  // RF-PUB-08: confirmación previa
      if (!confirm(t("publicaciones.confirmar_cierre"))) return;
      ocupado(boton, true);
      try {
        await api(`/api/publicaciones/${encodeURIComponent(p.id)}/cerrar`, { metodo: "POST" });
        alerta(mensajes, t("publicaciones.cerrada"), "success");
      } catch (error) { alerta(mensajes, error.message); }
      cargar();
    }

    cargar();
    setInterval(() => refrescarRestantes(lista), 30000);
  }
})();
