/* M01 — Acceso: registro, inicio de sesión, activación, recuperación y perfil. */
"use strict";

(() => {
  const { api, alerta, el, limpiar, ocupado, mostrarErrores, limpiarErrores, vaciarContrasenas, t } = Banca;
  const pagina = document.body.dataset.pagina;
  const mensajes = document.getElementById("mensajes");
  const valor = (id) => document.getElementById(id).value;

  function enviar(formulario, accion) {
    formulario.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      const boton = formulario.querySelector("[type=submit]");
      ocupado(boton, true);
      limpiarErrores(formulario);
      try { await accion(); } catch (error) {
        if (error.status !== 401 || pagina === "login") manejar(formulario, error);
        vaciarContrasenas(formulario);  // RNF-USA-06
      } finally { ocupado(boton, false); }
    });
  }

  function manejar(formulario, error) {
    const enCampo = mostrarErrores(formulario, error);  // RNF-USA-03
    const extras = [];
    if (error.codigo === "cuenta_pendiente" || error.codigo === "cuenta_no_activada" || error.codigo === "enlace_invalido") {
      extras.push(" ", el("a", { href: "/activar", class: "alert-link", text: t("acceso.solicitar_enlace") }));
    }
    if (error.codigo === "correo_registrado") extras.push(" ", el("a", { href: "/login", class: "alert-link", text: t("acceso.ir_a_iniciar_sesion") }));
    if (!enCampo || extras.length) alerta(mensajes, error.message, error.status === 429 ? "warning" : "danger", ...extras);
    else limpiar(mensajes);
  }

  if (pagina === "registro") {
    enviar(document.getElementById("form-registro"), async () => {
      const r = await api("/api/cuentas", { metodo: "POST", cuerpo: {
        correo: valor("correo"), nickname: valor("nickname"), contrasena: valor("contrasena"),
        confirmacion: valor("confirmacion"), acepta_terminos: document.getElementById("acepta_terminos").checked,
      } });
      document.getElementById("form-registro").reset();
      alerta(mensajes, r.mensaje, "success");
    });
  }

  if (pagina === "login") {
    enviar(document.getElementById("form-login"), async () => {
      await api("/api/sesiones", { metodo: "POST", cuerpo: { correo: valor("correo"), contrasena: valor("contrasena") } });
      location.href = "/feed";  // RF-AUT-08: mostrar el feed
    });
  }

  if (pagina === "activar") {
    const token = document.getElementById("token").dataset.token;
    const reenvio = document.getElementById("reenvio");
    if (token) {
      history.replaceState(null, "", "/activar");  // el token no queda en el historial
      api("/api/cuentas/activar", { metodo: "POST", cuerpo: { token } })
        .then((r) => { alerta(mensajes, r.mensaje, "success"); document.getElementById("continuar").classList.remove("d-none"); })
        .catch((error) => { alerta(mensajes, error.message); reenvio.classList.remove("d-none"); });
    }
    enviar(document.getElementById("form-reenvio"), async () => {
      const r = await api("/api/cuentas/activacion/reenviar", { metodo: "POST", cuerpo: { correo: valor("correo") } });
      alerta(mensajes, r.mensaje, "info");
    });
  }

  if (pagina === "recuperar") {
    enviar(document.getElementById("form-recuperar"), async () => {
      const r = await api("/api/contrasena/recuperar", { metodo: "POST", cuerpo: { correo: valor("correo") } });
      alerta(mensajes, r.mensaje, "info");
    });
  }

  if (pagina === "restablecer") {
    const token = document.getElementById("token").dataset.token;
    history.replaceState(null, "", "/restablecer");
    enviar(document.getElementById("form-restablecer"), async () => {
      try {
        const r = await api("/api/contrasena/restablecer", { metodo: "POST", cuerpo: {
          token, contrasena: valor("contrasena"), confirmacion: valor("confirmacion") } });
        document.getElementById("form-restablecer").classList.add("d-none");
        alerta(mensajes, r.mensaje, "success", " ", el("a", { href: "/login", class: "alert-link", text: t("acceso.iniciar_sesion") }));
      } catch (error) {
        if (error.codigo === "enlace_invalido") document.getElementById("acciones").classList.remove("d-none");
        throw error;
      }
    });
  }

  if (pagina === "perfil") {
    enviar(document.getElementById("form-nickname"), async () => {
      const r = await api("/api/cuentas/me/nickname", { metodo: "PATCH", cuerpo: { nickname: valor("nickname") } });
      const nav = document.getElementById("nav-nickname");
      if (nav) nav.textContent = `@${r.nickname}`;
      alerta(mensajes, t("acceso.nickname_actualizado"), "success");
    });
  }
})();
