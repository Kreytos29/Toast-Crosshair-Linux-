"""Servidor de instancia única.

Escucha el socket local y atiende las órdenes que mandan las demás ejecuciones
del programa (ver crosshair.ipc para el formato). Cada conexión es una línea
JSON de petición y otra de respuesta.
"""
import json
import logging

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QLocalServer

from ..ipc import send
from ..paths import runtime_socket

log = logging.getLogger(__name__)


class InstanceServer(QObject):
    """Recibe órdenes de otras ejecuciones. Quien conecte la señal debe
    devolver un diccionario con la respuesta."""

    command_received = pyqtSignal(str, object, object)  # orden, argumento, respuesta (dict)

    def __init__(self):
        super().__init__()
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._on_connection)

    def listen(self):
        path = runtime_socket()
        # Si quedó un socket de una sesión anterior que ya no atiende nadie, se
        # borra. Solo cuando de verdad no responde, para no robarle el sitio a
        # una instancia viva.
        if not send("ping", timeout=0.3):
            QLocalServer.removeServer(path)
        return self.server.listen(path)

    def close(self):
        self.server.close()

    def _on_connection(self):
        while self.server.hasPendingConnections():
            conn = self.server.nextPendingConnection()
            conn.readyRead.connect(lambda c=conn: self._read(c))
            conn.disconnected.connect(conn.deleteLater)
            self._read(conn)  # por si los datos ya llegaron

    def _read(self, conn):
        while conn.canReadLine():
            line = bytes(conn.readLine()).decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                command = str(request["cmd"])
                argument = request.get("arg")
            except (ValueError, KeyError, TypeError):
                log.warning("Orden mal formada: %r", line[:120])
                reply = {"ok": False, "error": "Orden mal formada."}
            else:
                reply = {"ok": True}
                self.command_received.emit(command, argument, reply)
            conn.write((json.dumps(reply) + "\n").encode("utf-8"))
            conn.flush()
