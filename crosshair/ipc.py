"""Comunicación con la instancia que ya está en ejecución.

Solo se permite una instancia del programa. Las demás ejecuciones le mandan una
orden por un socket local y terminan. Una línea JSON de ida y otra de vuelta:

    -> {"cmd": "toggle"}
    <- {"ok": true, "overlay": false}

Este módulo solo usa la biblioteca estándar, nunca Qt. Así un atajo de teclado
que ejecuta "crosshair --toggle" responde en milisegundos, sin esperar a que
cargue toda la interfaz.
"""
import json
import logging
import socket

from .paths import runtime_socket

log = logging.getLogger(__name__)

# Órdenes que acepta la instancia en ejecución
COMMANDS = ("show", "hide", "toggle", "on", "off", "status", "profile", "next-profile", "quit", "ping")


def send(command, argument=None, timeout=1.0):
    """Envía una orden y devuelve la respuesta, o None si no hay ninguna
    instancia en ejecución (o no contestó a tiempo)."""
    request = {"cmd": command}
    if argument is not None:
        request["arg"] = argument
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect(runtime_socket())
            sock.sendall((json.dumps(request) + "\n").encode("utf-8"))
            sock.shutdown(socket.SHUT_WR)
            chunks = []
            while b"\n" not in b"".join(chunks):
                chunk = sock.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
        line = b"".join(chunks).decode("utf-8", errors="replace").strip()
        return json.loads(line) if line else {"ok": True}
    except (OSError, ValueError) as error:
        log.debug("No se pudo enviar «%s»: %s", command, error)
        return None


def is_running():
    """True si ya hay una instancia atendiendo el socket."""
    return send("ping", timeout=0.5) is not None
