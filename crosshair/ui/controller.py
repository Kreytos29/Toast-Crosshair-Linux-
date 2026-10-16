"""Arranque y parada del proceso del overlay."""
import logging
import os
import sys

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, pyqtSignal

from ..paths import project_root

log = logging.getLogger(__name__)


class OverlayController(QObject):
    """Lanza y detiene crosshair.overlay como proceso aparte.

    Si se pulsa el atajo dos veces muy seguidas, la segunda llega mientras el
    overlay todavía se está cerrando. En vez de perderla, se recuerda y se
    vuelve a lanzar en cuanto el proceso anterior termina.
    """

    state_changed = pyqtSignal(bool)  # True = overlay activo

    def __init__(self):
        super().__init__()
        self._stopping = False  # se pidió cerrar el overlay y aún no termina
        self._restart = False   # se pidió activarlo otra vez mientras se cerraba
        self.proc = QProcess(self)
        # Los mensajes del overlay salen por la misma terminal; útil para depurar
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.ForwardedChannels)
        self.proc.setProcessEnvironment(self._environment())
        # Funciones sin argumentos: así PyQt no tiene que convertir los enums de
        # QProcess, que fallaba (y abortaba el programa) al cerrar con Ctrl+C
        self.proc.finished.connect(lambda: self._on_finished())
        self.proc.errorOccurred.connect(lambda: self.state_changed.emit(False))

    @staticmethod
    def _environment():
        """Entorno del overlay con la carpeta del proyecto en PYTHONPATH, para
        que «python -m crosshair.overlay» funcione también sin instalar."""
        env = QProcessEnvironment.systemEnvironment()
        root = str(project_root())
        existing = env.value("PYTHONPATH", "")
        if root not in existing.split(os.pathsep):
            env.insert("PYTHONPATH", os.pathsep.join([root, existing]) if existing else root)
        return env

    def is_running(self):
        return self.proc.state() != QProcess.ProcessState.NotRunning

    def is_active(self):
        """Estado deseado: el overlay está en marcha, o se está cerrando pero
        ya se pidió activarlo de nuevo."""
        return self.is_running() and (not self._stopping or self._restart)

    def _launch(self):
        log.debug("Lanzando el overlay")
        self.proc.start(sys.executable, ["-m", "crosshair.overlay"])
        self.state_changed.emit(True)

    def _on_finished(self):
        self._stopping = False
        if self._restart:
            self._restart = False
            self._launch()
        else:
            self.state_changed.emit(False)

    def start(self):
        if not self.is_running():
            self._launch()
        elif self._stopping:
            self._restart = True
            self.state_changed.emit(True)

    def stop(self):
        self._restart = False
        if self.is_running():
            if not self._stopping:
                self._stopping = True
                self.proc.terminate()
            self.state_changed.emit(False)

    def toggle(self):
        if self.is_active():
            self.stop()
        else:
            self.start()

    def shutdown(self):
        """Cierra el overlay al salir de la aplicación."""
        self._restart = False
        if self.is_running():
            self._stopping = True
            self.proc.terminate()
            if not self.proc.waitForFinished(1500):
                log.warning("El overlay no respondió; se cierra a la fuerza")
                self.proc.kill()
