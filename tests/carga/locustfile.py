"""Prueba de carga de RNF-REN-01/02/03/06 (Locust). La orquesta tests/carga/ejecutar_carga.py.

Uso directo (con la base preparada por ejecutar_carga.py y la app en marcha):
    locust -f tests/carga/locustfile.py --headless -u 100 -r 10 --run-time 15m --host http://127.0.0.1:8000

Cada usuario virtual usa su propia cuenta de las 10 000 sembradas (carga00000@unas.edu.pe … con la misma
contraseña) para que el límite de publicaciones y los chats no se mezclen entre usuarios.
"""
import itertools
import random
import sys
import time
from pathlib import Path

from locust import HttpUser, constant_pacing, task
from locust.clients import HttpSession

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perfil  # noqa: E402

CLAVE = "clave123"
AUTOMATICA = {"X-Actualizacion-Automatica": "1"}  # sondeos: no reinician la inactividad (RF-AUT-25)
TIPOS = ["NECESITO", "OFREZCO", "ACTIVIDAD"]
_lectores, _conversadores, _publicadores = itertools.count(5000), itertools.count(7000, 2), itertools.count(9000)


def correo(n: int) -> str:
    return f"carga{n:05d}@unas.edu.pe"


def iniciar_sesion(cliente, n: int) -> None:
    with cliente.post("/api/sesiones", json={"correo": correo(n), "contrasena": CLAVE}, name="iniciar sesión",
                      catch_response=True) as r:
        if r.status_code != 200:
            r.failure(f"inicio de sesión {r.status_code}: {r.text[:200]}")


class LectorFeed(HttpUser):
    """60 %: consulta el feed cada 30 s; la mitad de las consultas con filtro por tipo (RNF-REN-02)."""

    weight, _pausa = perfil.PERFIL["LectorFeed"]
    wait_time = constant_pacing(_pausa)

    def on_start(self):
        iniciar_sesion(self.client, next(_lectores))

    @task
    def consultar_feed(self):
        if random.random() < 0.5:
            self.client.get("/api/feed", params={"tipo": random.choice(TIPOS)}, name=perfil.FEED_FILTRO)
        else:
            self.client.get("/api/feed", name=perfil.FEED)


class Conversador(HttpUser):
    """30 %: un chat 1 a 1 entre dos cuentas; envía un mensaje cada 20 s y el otro participante sondea cada 1 s,
    como la página del chat abierto. Mide el tiempo desde el envío hasta que el otro lo recibe (RNF-REN-03)."""

    weight, _pausa = perfil.PERFIL["Conversador"]
    wait_time = constant_pacing(_pausa)

    def on_start(self):
        n = next(_conversadores)
        self.otro = HttpSession(base_url=self.host, request_event=self.environment.events.request, user=self)
        iniciar_sesion(self.client, n)
        iniciar_sesion(self.otro, n + 1)
        r = self.client.post("/api/publicaciones", json={"tipo": "ACTIVIDAD", "titulo": f"Chat de carga {n}",
                                                         "descripcion": "Prueba de carga"}, name="crear publicación")
        r2 = self.otro.post(f"/api/publicaciones/{r.json()['id']}/respuestas", data={"texto": "Hola"},
                            name="responder publicación")
        self.chat = r2.json()["chat_id"]
        self.lados = [(self.client, self.otro), (self.otro, self.client)]
        self.vistos = {lado: None for lado in (0, 1)}
        self.turno = 0

    @task
    def intercambiar_mensaje(self):
        emisor, receptor = self.lados[self.turno]
        lado_receptor = 1 - self.turno
        self.turno = lado_receptor
        inicio = time.perf_counter()
        r = emisor.post(f"/api/chats/{self.chat}/mensajes", data={"texto": f"mensaje {time.time():.3f}"},
                        name="enviar mensaje de texto")
        if r.status_code != 201:
            return
        mensaje = r.json()["id"]
        entregado, limite = False, inicio + self._pausa - 1.5
        while time.perf_counter() < limite:  # el chat sigue abierto: sondeo de 1 s del otro participante
            antes = time.perf_counter()
            params = {"despues_de": self.vistos[lado_receptor]} if self.vistos[lado_receptor] else {}
            sondeo = receptor.get(f"/api/chats/{self.chat}", params=params, headers=AUTOMATICA,
                                  name="sondeo del chat abierto (1 s)")
            if sondeo.status_code == 200:
                nuevos = sondeo.json()["mensajes"]
                if nuevos:
                    self.vistos[lado_receptor] = nuevos[-1]["fecha_envio"]
                if not entregado and any(m["id"] == mensaje for m in nuevos):
                    entregado = True
                    self.environment.events.request.fire(
                        request_type="ENTREGA", name=perfil.ENTREGA_TEXTO, response_time=(time.perf_counter() - inicio) * 1000,
                        response_length=0, exception=None, context={})
            time.sleep(max(0.0, 1.0 - (time.perf_counter() - antes)))
        if not entregado:
            self.environment.events.request.fire(
                request_type="ENTREGA", name=perfil.ENTREGA_TEXTO, response_time=(time.perf_counter() - inicio) * 1000,
                response_length=0, exception=TimeoutError("el mensaje no llegó al otro participante"), context={})


class Publicador(HttpUser):
    """10 %: crea o cierra una publicación cada 2 min (alterna para no superar el límite de activas)."""

    weight, _pausa = perfil.PERFIL["Publicador"]
    wait_time = constant_pacing(_pausa)

    def on_start(self):
        iniciar_sesion(self.client, next(_publicadores))
        self.abierta = None

    @task
    def crear_o_cerrar(self):
        if self.abierta is None:
            r = self.client.post("/api/publicaciones", json={"tipo": random.choice(TIPOS), "titulo": "Publicación de carga",
                                                             "descripcion": "Generada por la prueba de carga"},
                                 name="crear publicación")
            self.abierta = r.json().get("id") if r.status_code == 201 else None
        else:
            self.client.post(f"/api/publicaciones/{self.abierta}/cerrar", name="cerrar publicación")
            self.abierta = None
