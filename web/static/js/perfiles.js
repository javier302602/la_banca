/* M07 — Perfiles (SRS v2.0): editar foto, avatar y biografía (CU-19) y ver un perfil (CU-20). */
"use strict";

(() => {
  const { api, alerta, limpiar, ocupado, mostrarErrores, limpiarErrores, contador, comprimirImagen, pintarAvatar,
          formatoFecha, t } = Banca;
  const pagina = document.body.dataset.pagina;
  const TAMANO_MAX_FOTO = 2 * 1024 * 1024;

  /* ---- CU-19: /perfil ---------------------------------------------------------------------------------------- */
  function mostrarPerfil(r) {
    pintarAvatar(document.getElementById("vista-avatar"), r.apariencia);
    // La muestra de «Mis iniciales» usa siempre las iniciales, aunque haya foto o avatar
    pintarAvatar(document.getElementById("muestra-iniciales"),
                 { tipo: "iniciales", iniciales: r.apariencia.iniciales, color: r.apariencia.color });
    document.getElementById("quitar-foto").classList.toggle("d-none", !r.tiene_foto);
  }

  async function prepararEdicion() {
    const avisos = document.getElementById("mensajes-perfil");
    const formFoto = document.getElementById("form-foto");
    const formPerfil = document.getElementById("form-perfil");
    const biografia = document.getElementById("biografia");
    const entradaFoto = document.getElementById("foto");
    contador(biografia, document.getElementById("contador-biografia"), 160);

    const cargar = async () => {
      const r = await api("/api/cuentas/me/perfil");
      biografia.value = r.biografia;
      biografia.dispatchEvent(new Event("input"));
      const elegido = document.getElementById(r.avatar ? `avatar-${r.avatar}` : "avatar-ninguno");
      if (elegido) elegido.checked = true;
      mostrarPerfil(r);
    };
    try { await cargar(); } catch (e) { alerta(avisos, e.message); }
    document.addEventListener("banca:nickname", () => { cargar().catch(() => {}); });

    formPerfil.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      const boton = formPerfil.querySelector("[type=submit]");
      ocupado(boton, true);
      limpiarErrores(formPerfil);
      limpiar(avisos);
      try {
        const elegido = formPerfil.querySelector("input[name=avatar]:checked");
        const r = await api("/api/cuentas/me/perfil", { metodo: "PATCH", cuerpo: {
          biografia: biografia.value, avatar: elegido && elegido.value ? elegido.value : null } });
        mostrarPerfil(r);
        alerta(avisos, t("perfil.guardado"), "success");
      } catch (error) {
        if (!mostrarErrores(formPerfil, error)) alerta(avisos, error.message);
      } finally { ocupado(boton, false); }
    });

    formFoto.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      const boton = formFoto.querySelector("[type=submit]");
      limpiarErrores(formFoto);
      limpiar(avisos);
      ocupado(boton, true);
      try {
        // Compresión en el navegador (como en el chat); el servidor vuelve a validar y recortar
        const archivo = await comprimirImagen(entradaFoto.files[0], TAMANO_MAX_FOTO);
        const datos = new FormData();
        if (archivo) datos.append("foto", archivo);
        const r = await api("/api/cuentas/me/foto", { metodo: "PUT", formulario: datos });
        formFoto.reset();
        mostrarPerfil(r);
        alerta(avisos, t("perfil.foto_subida"), "success");
      } catch (error) {
        if (!mostrarErrores(formFoto, error)) alerta(avisos, error.message);
      } finally { ocupado(boton, false); }
    });

    document.getElementById("quitar-foto").addEventListener("click", async (evento) => {
      const boton = evento.currentTarget;
      limpiar(avisos);
      ocupado(boton, true);
      try {
        mostrarPerfil(await api("/api/cuentas/me/foto", { metodo: "DELETE" }));
        alerta(avisos, t("perfil.foto_quitada"), "success");
        document.getElementById("foto").focus();  // el botón desaparece: el foco no se pierde
      } catch (error) { alerta(avisos, error.message); } finally { ocupado(boton, false); }
    });
  }

  /* ---- CU-20: /perfiles/{nickname} --------------------------------------------------------------------------- */
  async function mostrarPublico() {
    const tarjeta = document.getElementById("perfil");
    try {
      const p = await api(`/api/perfiles/${encodeURIComponent(tarjeta.dataset.nickname)}`);
      pintarAvatar(document.getElementById("perfil-avatar"), p.apariencia);
      document.getElementById("perfil-nickname").textContent = t("perfil.titulo", { nickname: p.nickname });
      document.getElementById("perfil-ingreso").textContent = t("perfil.ingreso", { fecha: formatoFecha(p.fecha_ingreso) });
      const bio = document.getElementById("perfil-biografia");
      bio.textContent = p.biografia || t("perfil.sin_biografia");
      bio.classList.toggle("text-body-secondary", !p.biografia);
      if (p.es_propio) {
        document.getElementById("perfil-propio-texto").textContent = t("perfil.es_propio");
        document.getElementById("perfil-propio").hidden = false;
      }
      document.title = t("perfil.ver", { nickname: p.nickname }) + " · " + document.title.split(" · ").pop();
      tarjeta.hidden = false;
    } catch (error) {
      alerta(document.getElementById("mensajes"), error.message, error.status === 404 ? "warning" : "danger");
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (pagina === "perfil") prepararEdicion();
    if (pagina === "ver-perfil") mostrarPublico();
  });
})();
