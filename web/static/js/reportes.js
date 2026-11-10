/* M05 — Reportar una publicación (CU-13) o un chat (CU-14). */
"use strict";

(() => {
  const { api, alerta, el, limpiar, contador, ocupado, mostrarErrores, limpiarErrores, t } = Banca;
  const formulario = document.getElementById("form-reporte");
  if (!formulario) return;
  const mensajes = document.getElementById("mensajes");
  const destino = document.getElementById("destino").dataset;
  const enviar = document.getElementById("enviar");
  contador(document.getElementById("observacion"), document.getElementById("contador-observacion"), 300);

  // RF-REP-03: sin motivo seleccionado no se permite enviar
  formulario.addEventListener("change", () => {
    enviar.disabled = !formulario.querySelector("input[name=codigo_motivo]:checked");
  });

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const motivo = formulario.querySelector("input[name=codigo_motivo]:checked");
    if (!motivo) return;
    ocupado(enviar, true);
    limpiarErrores(formulario);
    try {
      const r = await api(destino.url, { metodo: "POST", cuerpo: {
        codigo_motivo: motivo.value, observacion: document.getElementById("observacion").value || null } });
      formulario.classList.add("d-none");
      alerta(mensajes, r.mensaje, "success", " ", el("a", { class: "alert-link", href: destino.volver, text: t("reportes.volver") }));
    } catch (error) {
      if (error.status !== 401) {
        if (mostrarErrores(formulario, error)) limpiar(mensajes); else alerta(mensajes, error.message);
      }
      ocupado(enviar, false);
    }
  });
})();
