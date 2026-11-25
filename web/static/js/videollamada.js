/* M08 — Videollamada aleatoria (CU-23) y reporte (CU-24).
 *
 * El audio y el video van directo entre los dos navegadores (WebRTC). El WebSocket /ws/videollamada solo sirve
 * para entrar a la cola, saber con quién te emparejaron e intercambiar las «señales» (oferta, respuesta y
 * candidatos ICE) y el chat de texto. Nada se graba.
 *   empezar → permiso de cámara y micrófono → buscar → emparejado → oferta/respuesta → llamada
 *   Siguiente: cuelga y busca otra persona · Colgar: termina y apaga la cámara · Reportar: reporte y siguiente
 */
"use strict";

(() => {
  if (document.body.dataset.pagina !== "videollamada") return;
  const { api, alerta, limpiar, el, t, icono } = Banca;
  const $ = (id) => document.getElementById(id);
  const mensajes = $("mensajes");
  const servidoresIce = JSON.parse($("config-llamada").dataset.servidoresIce || "[]");
  const estado = $("estado-llamada");
  const remoto = $("video-remoto");
  const propio = $("video-propio");
  const formChat = $("form-chat-llamada");
  const textoChat = $("texto-llamada");
  const historial = $("historial-llamada");
  const botonReportar = $("boton-reportar");
  let flujoPropio = null, socket = null, conexion = null, sala = null, pareja = null;
  let candidatosPendientes = [], terminando = false, cola = Promise.resolve();

  function decir(clave) {
    estado.textContent = t(clave);
    estado.hidden = false;
  }

  function habilitarLlamada(activa) {
    textoChat.disabled = !activa;
    formChat.querySelector("[type=submit]").disabled = !activa;
    botonReportar.disabled = !activa;
  }

  function mostrarPareja(p) {
    $("pareja").hidden = !p;
    if (!p) return;
    $("pareja-nombre").textContent = p.nombre;
    $("pareja-carrera").textContent = p.carrera;
    $("pareja-nickname").textContent = `@${p.nickname}`;
  }

  function agregarChat(texto, esPropio) {
    const quien = esPropio ? t("videollamada.tu") : pareja ? pareja.nombre : "";
    historial.append(el("p", { class: `mensaje-llamada${esPropio ? " propio" : ""}` },
      el("strong", { text: `${quien}: ` }), el("span", { text: texto })));
    historial.scrollTop = historial.scrollHeight;
  }

  const enviar = (mensaje) => { if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(mensaje)); };

  /* ---- WebRTC ------------------------------------------------------------------------------------------- */
  function cerrarConexion() {
    if (conexion) conexion.close();
    conexion = null;
    sala = null;
    pareja = null;
    candidatosPendientes = [];
    remoto.srcObject = null;
    mostrarPareja(null);
    habilitarLlamada(false);
  }

  async function iniciarConexion(m) {
    cerrarConexion();
    sala = m.sala;
    pareja = m.pareja;
    mostrarPareja(pareja);
    historial.replaceChildren();
    habilitarLlamada(true);
    decir("videollamada.conectando");
    conexion = new RTCPeerConnection({ iceServers: servidoresIce });
    flujoPropio.getTracks().forEach((pista) => conexion.addTrack(pista, flujoPropio));
    conexion.addEventListener("track", (evento) => { remoto.srcObject = evento.streams[0]; });
    conexion.addEventListener("icecandidate", (evento) => {
      if (evento.candidate) enviar({ tipo: "senal", datos: { candidato: evento.candidate.toJSON() } });
    });
    conexion.addEventListener("connectionstatechange", () => {
      if (!conexion) return;
      if (conexion.connectionState === "connected") estado.hidden = true;
      if (conexion.connectionState === "failed") decir("videollamada.fallo");
    });
    if (m.iniciador) {  // quien empareja crea la oferta; la otra persona responde
      await conexion.setLocalDescription(await conexion.createOffer());
      enviar({ tipo: "senal", datos: { descripcion: conexion.localDescription.toJSON() } });
    }
  }

  async function recibirSenal(datos) {
    if (!conexion) return;
    if (datos.descripcion) {
      await conexion.setRemoteDescription(datos.descripcion);
      for (const candidato of candidatosPendientes) await conexion.addIceCandidate(candidato);
      candidatosPendientes = [];
      if (datos.descripcion.type === "offer") {
        await conexion.setLocalDescription(await conexion.createAnswer());
        enviar({ tipo: "senal", datos: { descripcion: conexion.localDescription.toJSON() } });
      }
    } else if (datos.candidato) {
      // un candidato puede llegar antes que la descripción remota: se guarda hasta tenerla
      if (conexion.remoteDescription) await conexion.addIceCandidate(datos.candidato);
      else candidatosPendientes.push(datos.candidato);
    }
  }

  /* ---- Mensajes del servidor (se procesan en orden, uno tras otro) --------------------------------------- */
  async function recibir(m) {
    if (m.tipo === "esperando") { mostrarPareja(null); decir("videollamada.buscando"); }
    else if (m.tipo === "emparejado") await iniciarConexion(m);
    else if (m.tipo === "senal") await recibirSenal(m.datos);
    else if (m.tipo === "chat") agregarChat(m.texto, false);
    else if (m.tipo === "colgo") {  // la otra persona se fue: como en las apps de este tipo, se busca a otra
      cerrarConexion();
      decir("videollamada.se_fue");
      setTimeout(() => { if (!terminando && !sala) enviar({ tipo: "buscar" }); }, 1500);
    } else if (m.tipo === "error") alerta(mensajes, m.mensaje);
  }

  function conectar() {
    const esquema = location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${esquema}://${location.host}/ws/videollamada`);
    socket.addEventListener("open", () => enviar({ tipo: "buscar" }));
    socket.addEventListener("message", (evento) => {
      const m = JSON.parse(evento.data);
      cola = cola.then(() => recibir(m)).catch((error) => console.error(error));
    });
    socket.addEventListener("close", (evento) => {
      cerrarConexion();
      if (!terminando) decir(evento.code === 4403 ? "videollamada.falta_perfil" : "videollamada.desconectado");
    });
  }

  /* ---- Controles ----------------------------------------------------------------------------------------- */
  async function empezar() {
    limpiar(mensajes);
    try {
      flujoPropio = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    } catch (e) {
      alerta(mensajes, t("videollamada.sin_permiso"));
      return;
    }
    terminando = false;
    propio.srcObject = flujoPropio;
    $("inicio-llamada").hidden = true;
    $("llamada").hidden = false;
    conectar();
  }

  function colgar() {
    terminando = true;
    enviar({ tipo: "colgar" });
    if (socket) socket.close();
    cerrarConexion();
    if (flujoPropio) flujoPropio.getTracks().forEach((pista) => pista.stop());  // apaga la cámara de verdad
    flujoPropio = null;
    propio.srcObject = null;
    $("llamada").hidden = true;
    $("inicio-llamada").hidden = false;
    $("empezar").focus();
  }

  function alternar(boton, tipo, claveActivo, claveInactivo, iconoActivo, iconoInactivo) {
    if (!flujoPropio) return;
    const pistas = tipo === "audio" ? flujoPropio.getAudioTracks() : flujoPropio.getVideoTracks();
    const apagado = boton.getAttribute("aria-pressed") !== "true";  // pulsado = apagado
    pistas.forEach((pista) => { pista.enabled = !apagado; });
    boton.setAttribute("aria-pressed", String(apagado));
    boton.replaceChildren(icono(apagado ? iconoInactivo : iconoActivo), ` ${t(apagado ? claveInactivo : claveActivo)}`);
  }

  const empezarBoton = $("empezar");
  if (empezarBoton) empezarBoton.addEventListener("click", empezar);
  $("boton-colgar").addEventListener("click", colgar);
  $("boton-siguiente").addEventListener("click", () => { cerrarConexion(); enviar({ tipo: "siguiente" }); });
  $("boton-microfono").addEventListener("click", (e) => alternar(e.currentTarget, "audio",
    "videollamada.silenciar", "videollamada.activar_microfono", "bi-mic-mute", "bi-mic"));
  $("boton-camara").addEventListener("click", (e) => alternar(e.currentTarget, "video",
    "videollamada.apagar_camara", "videollamada.encender_camara", "bi-camera-video-off", "bi-camera-video"));

  formChat.addEventListener("submit", (evento) => {
    evento.preventDefault();
    const texto = textoChat.value.trim();
    if (!texto || !sala) return;
    enviar({ tipo: "chat", texto });
    agregarChat(texto, true);
    textoChat.value = "";
  });

  /* ---- Reportar (CU-24): se reporta la sala actual; luego se pasa a otra persona ---------------------------- */
  const dialogo = $("dialogo-reporte");
  let salaReportada = null;
  botonReportar.addEventListener("click", () => {
    salaReportada = sala;
    dialogo.showModal();
  });
  $("cancelar-reporte").addEventListener("click", () => dialogo.close());
  $("form-reporte").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const motivo = $("form-reporte").querySelector("input[name=motivo]:checked").value;
    try {
      const r = await api("/api/videollamada/reportes", { metodo: "POST", cuerpo: {
        sala_id: salaReportada, motivo, detalle: $("detalle-reporte").value } });
      dialogo.close();
      $("detalle-reporte").value = "";
      alerta(mensajes, r.mensaje, "success");
      if (sala === salaReportada) { cerrarConexion(); enviar({ tipo: "siguiente" }); }
    } catch (error) {
      dialogo.close();
      if (error.status !== 401) alerta(mensajes, error.message);
    }
  });
})();
