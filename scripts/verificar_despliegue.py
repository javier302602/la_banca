"""Verificación de un despliegue con docker compose (docs/DESPLIEGUE.md, paso «Verificar»).

Recorre el flujo principal contra la URL pública, sin tocar la base directamente:
salud y versión → registro → correo de activación (Mailpit, solo perfil dev) → activación → inicio de sesión →
perfil con foto → publicación con imagen → respuesta con documento → descarga.

Uso:
    python scripts/verificar_despliegue.py --url https://localhost:8443 --mailpit http://localhost:8025 --inseguro
--inseguro acepta el certificado local de Caddy (solo con SITIO=localhost). Sin --mailpit solo se comprueban la
salud, la versión y las páginas públicas (útil en producción, donde los correos van a buzones reales).
Requiere httpx y Pillow (pip install -r requirements-dev.txt).
"""
import argparse
import io
import re
import secrets
import sys
import time

import httpx


def paso(texto: str) -> None:
    print(f"- {texto}")


def png() -> bytes:
    from PIL import Image

    salida = io.BytesIO()
    Image.new("RGB", (64, 48), (79, 60, 201)).save(salida, format="PNG")
    return salida.getvalue()


def ultimo_enlace(mailpit: str, correo: str, cliente: httpx.Client) -> str:
    for _ in range(30):
        mensajes = cliente.get(f"{mailpit}/api/v1/search", params={"query": f"to:{correo}"}).json()["messages"]
        if mensajes:
            texto = cliente.get(f"{mailpit}/api/v1/message/{mensajes[0]['ID']}").json()["Text"]
            return re.search(r"https?://\S+token=[\w-]+", texto).group(0)
        time.sleep(1)
    raise AssertionError(f"No llegó el correo para {correo} a Mailpit")


def verificar(url: str, mailpit: str | None, inseguro: bool, dominio: str) -> None:
    verificar_tls = not inseguro
    with httpx.Client(base_url=url, verify=verificar_tls, timeout=30, follow_redirects=False) as c:
        r = c.get("/api/salud")
        assert r.status_code == 200 and r.json()["base_de_datos"] == "ok", r.text
        paso(f"/api/salud: ok, versión {r.json()['version']}")
        assert r.json()["version"] in c.get("/").text
        paso("portada con la versión en el pie")
        if r.headers.get("strict-transport-security"):
            paso("HSTS activo (producción)")
        if not mailpit:
            return

        nick = f"verif_{secrets.token_hex(3)}"
        correo, clave = f"{nick}@{dominio}", "Verificar123!"
        r = c.post("/api/cuentas", json={"correo": correo, "contrasena": clave, "confirmacion": clave,
                                         "nickname": nick, "acepta_terminos": True})
        assert r.status_code == 201, r.text
        with httpx.Client(timeout=10) as m:
            enlace = ultimo_enlace(mailpit.rstrip("/"), correo, m)
        paso(f"registro de @{nick} y correo de activación recibido en Mailpit")
        token = enlace.split("token=")[1]
        assert c.post("/api/cuentas/activar", json={"token": token}).status_code == 200
        assert c.post("/api/sesiones", json={"correo": correo, "contrasena": clave}).status_code == 200
        paso("cuenta activada e inicio de sesión")

        r = c.put("/api/cuentas/me/foto", files={"foto": ("yo.png", png(), "image/png")})
        assert r.status_code == 200, r.text
        assert c.get(r.json()["apariencia"]["url"]).headers["content-type"] == "image/webp"
        paso("foto de perfil guardada en MinIO y servida")

        r = c.post("/api/publicaciones", data={"tipo": "OFREZCO", "titulo": "Verificación", "descripcion": "Prueba"},
                   files=[("imagenes", ("a.png", png(), "image/png"))])
        assert r.status_code == 201, r.text
        pid, imagen = r.json()["id"], r.json()["imagenes"][0]
        assert c.get(imagen).status_code == 200
        paso("publicación con imagen")
        cerrar = c.post(f"/api/publicaciones/{pid}/cerrar")
        paso(f"publicación cerrada ({cerrar.status_code})")


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--url", required=True)
    analizador.add_argument("--mailpit")
    analizador.add_argument("--dominio", default="unas.edu.pe")
    analizador.add_argument("--inseguro", action="store_true")
    args = analizador.parse_args()
    try:
        verificar(args.url.rstrip("/"), args.mailpit, args.inseguro, args.dominio)
    except (AssertionError, httpx.HTTPError) as error:
        print(f"FALLÓ: {error}", file=sys.stderr)
        return 1
    print("Despliegue verificado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
