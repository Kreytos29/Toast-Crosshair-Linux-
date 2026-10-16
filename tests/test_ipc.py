"""Comunicación entre la instancia en ejecución y las demás ejecuciones."""
import threading
import unittest

import sandbox  # debe importarse primero: aísla la configuración del usuario

from crosshair import ipc

try:
    from PyQt6.QtWidgets import QApplication
    HAVE_QT = True
except ImportError:  # pragma: no cover
    HAVE_QT = False

qapp = None


def setUpModule():
    if not HAVE_QT:
        raise unittest.SkipTest("hace falta PyQt6")
    global qapp
    qapp = QApplication.instance() or QApplication([])
    sandbox.reset()


class TestServidor(unittest.TestCase):
    def setUp(self):
        from crosshair.ui.server import InstanceServer

        self.recibido = []
        self.server = InstanceServer()
        self.assertTrue(self.server.listen(), "el socket debería poder crearse")
        self.server.command_received.connect(self._handle)

    def tearDown(self):
        self.server.close()

    def _handle(self, command, argument, reply):
        self.recibido.append((command, argument))
        if command == "desconocida":
            reply.update(ok=False, error="no existe")
        else:
            reply.update(eco=command, arg=argument)

    def send(self, *args):
        """Envía desde otro hilo mientras Qt atiende el socket en este."""
        out = {}

        def worker():
            out["reply"] = ipc.send(*args)

        thread = threading.Thread(target=worker)
        thread.start()
        while thread.is_alive():
            QApplication.processEvents()
        thread.join()
        return out["reply"]

    def test_una_orden_simple_va_y_vuelve(self):
        reply = self.send("toggle")
        self.assertEqual(reply["ok"], True)
        self.assertEqual(reply["eco"], "toggle")
        self.assertEqual(self.recibido, [("toggle", None)])

    def test_una_orden_con_argumento(self):
        reply = self.send("profile", "Punto verde")
        self.assertEqual(reply["arg"], "Punto verde")
        self.assertEqual(self.recibido, [("profile", "Punto verde")])

    def test_el_error_llega_al_que_pregunta(self):
        reply = self.send("desconocida")
        self.assertFalse(reply["ok"])
        self.assertEqual(reply["error"], "no existe")

    def test_is_running_detecta_el_servidor(self):
        out = {}

        def worker():
            out["v"] = ipc.is_running()

        thread = threading.Thread(target=worker)
        thread.start()
        while thread.is_alive():
            QApplication.processEvents()
        thread.join()
        self.assertTrue(out["v"])

    def test_un_acento_sobrevive_al_viaje(self):
        reply = self.send("profile", "Círculo cián ñ")
        self.assertEqual(reply["arg"], "Círculo cián ñ")


class TestSinServidor(unittest.TestCase):
    def test_sin_instancia_devuelve_none(self):
        self.assertIsNone(ipc.send("toggle", timeout=0.3))

    def test_is_running_es_falso(self):
        self.assertFalse(ipc.is_running())


if __name__ == "__main__":
    unittest.main()
