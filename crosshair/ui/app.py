"""Proceso de la interfaz: icono en la bandeja, ventana de ajustes y control
del overlay. Es también el que atiende las órdenes de la línea de comandos.
"""
import logging
import signal
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .. import __version__
from ..config import load_profiles, next_profile_name, profile_appearance, profile_order
from ..paths import DESKTOP_NAME
from .controller import OverlayController
from .icons import app_icon, tray_icon
from .server import InstanceServer
from .theme import STYLESHEET
from .window import SettingsWindow

log = logging.getLogger(__name__)

TRAY_RETRY_MS = 1000
TRAY_MAX_RETRIES = 30


class Application:
    """Junta la bandeja, la ventana y el control del overlay."""

    def __init__(self, qapp, hidden):
        self.qapp = qapp
        self.controller = OverlayController()
        self.window = SettingsWindow(self.controller)
        self.controller.state_changed.connect(self.on_overlay_state)

        self.server = InstanceServer()
        if not self.server.listen():
            log.warning("No se pudo crear el socket de instancia única; los atajos no funcionarán.")
        self.server.command_received.connect(self.on_command)

        self._build_tray()
        self.qapp.aboutToQuit.connect(self.controller.shutdown)

        self.controller.start()
        if not hidden:
            self.show_window()

    # --- bandeja ------------------------------------------------------------
    def _build_tray(self):
        self.tray = QSystemTrayIcon(tray_icon(False))
        self.tray.setToolTip("Crosshair")

        menu = QMenu()
        menu.setStyleSheet(STYLESHEET)

        self.toggle_action = QAction("Mira activa", menu)
        self.toggle_action.setCheckable(True)
        self.toggle_action.triggered.connect(
            lambda checked: self.controller.start() if checked else self.controller.stop()
        )
        menu.addAction(self.toggle_action)

        self.profiles_menu = QMenu("Perfil", menu)
        self.profiles_menu.aboutToShow.connect(self._fill_profiles_menu)
        menu.addMenu(self.profiles_menu)

        next_action = QAction("Perfil siguiente", menu)
        next_action.triggered.connect(lambda: self.apply_profile(None))
        menu.addAction(next_action)

        menu.addSeparator()
        settings_action = QAction("Ajustes…", menu)
        settings_action.triggered.connect(self.show_window)
        menu.addAction(settings_action)

        menu.addSeparator()
        quit_action = QAction("Salir", menu)
        quit_action.triggered.connect(self.qapp.quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()
        self._watch_for_tray()

    def _fill_profiles_menu(self):
        """La lista se rehace al abrir el menú: los perfiles pueden haber
        cambiado desde la ventana de ajustes o editando el archivo."""
        self.profiles_menu.clear()
        profiles = load_profiles()
        current = self.window.current_look()
        for name in profile_order(profiles):
            action = QAction(name, self.profiles_menu)
            action.setCheckable(True)
            found = profile_appearance(name, profiles)
            action.setChecked(bool(found) and found[0] == current)
            action.triggered.connect(lambda _checked=False, n=name: self.apply_profile(n))
            self.profiles_menu.addAction(action)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.window.hide() if self.window.isVisible() else self.show_window()

    def _watch_for_tray(self):
        """Al iniciar con la sesión, la bandeja del escritorio puede tardar en
        estar lista: se reintenta un rato. Si nunca aparece, se abre la ventana
        para no dejar el programa sin ninguna interfaz visible."""
        if QSystemTrayIcon.isSystemTrayAvailable():
            return
        timer = QTimer(self.qapp)
        timer.setInterval(TRAY_RETRY_MS)
        attempts = {"n": 0}

        def retry():
            attempts["n"] += 1
            if QSystemTrayIcon.isSystemTrayAvailable():
                timer.stop()
                self.tray.hide()
                self.tray.show()
            elif attempts["n"] >= TRAY_MAX_RETRIES:
                timer.stop()
                log.warning("No se detectó una bandeja del sistema; se abre la ventana de ajustes.")
                self.show_window()

        timer.timeout.connect(retry)
        timer.start()
        self._tray_timer = timer

    # --- acciones -----------------------------------------------------------
    def show_window(self):
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def on_overlay_state(self, running):
        # La ventana se entera por su cuenta; aquí solo se actualiza la bandeja
        self.toggle_action.setChecked(running)
        self.tray.setIcon(tray_icon(running))
        self.tray.setToolTip("Crosshair · mira activa" if running else "Crosshair · mira inactiva")

    def apply_profile(self, name):
        """Aplica un perfil por su nombre, o pasa al siguiente si name es None.
        Devuelve el nombre aplicado, o None si no existe."""
        profiles = load_profiles()
        if name is None:
            name = next_profile_name(self.window.cfg, profiles)
        found = profile_appearance(name, profiles) if name else None
        if found is None:
            return None
        look, real_name = found
        self.window.apply_look(look)
        return real_name

    # --- órdenes de otras ejecuciones --------------------------------------
    def on_command(self, command, argument, reply):
        log.debug("Orden recibida: %s %r", command, argument)
        if command == "show":
            self.show_window()
        elif command == "hide":
            self.window.hide()
        elif command == "toggle":
            self.controller.toggle()
        elif command == "on":
            self.controller.start()
        elif command == "off":
            self.controller.stop()
        elif command == "quit":
            QTimer.singleShot(0, self.qapp.quit)
        elif command in ("profile", "next-profile"):
            applied = self.apply_profile(argument if command == "profile" else None)
            if applied is None:
                reply.update(ok=False, error=f"No existe el perfil «{argument}».")
                return
        elif command not in ("ping", "status"):
            # «ping» y «status» no hacen nada: la respuesta de abajo ya lleva
            # todo lo que piden
            reply.update(ok=False, error=f"Orden desconocida: {command}")
            return
        reply.update(self.status())

    def status(self):
        cfg = self.window.cfg
        profiles = load_profiles()
        current = self.window.current_look()
        name = next((n for n in profile_order(profiles)
                     if (profile_appearance(n, profiles) or (None,))[0] == current), None)
        return {
            "version": __version__,
            "overlay": self.controller.is_active(),
            "profile": name,
            "monitor": cfg["monitor"],
            "offset_x": cfg["offset_x"],
            "offset_y": cfg["offset_y"],
        }


def run(hidden=False, debug=False):
    qapp = QApplication(sys.argv)
    qapp.setStyle("Fusion")  # base uniforme sobre la que se aplica el tema propio
    qapp.setApplicationName("Crosshair")
    qapp.setApplicationVersion(__version__)
    # Nombre estable de la ventana en Wayland; de aquí sale la clase que usan
    # las reglas de ventana de Hyprland
    qapp.setDesktopFileName(DESKTOP_NAME)
    qapp.setWindowIcon(app_icon())
    qapp.setQuitOnLastWindowClosed(False)  # seguir en la bandeja al cerrar la ventana

    # Hay que guardar la referencia o Python eliminaría la bandeja y la ventana
    qapp.crosshair = Application(qapp, hidden)

    # Ctrl+C y SIGTERM cierran de forma ordenada. El temporizador deja que
    # Python atienda las señales mientras Qt está en su bucle de eventos.
    signal.signal(signal.SIGINT, lambda *_: qapp.quit())
    signal.signal(signal.SIGTERM, lambda *_: qapp.quit())
    ticker = QTimer()
    ticker.start(250)
    ticker.timeout.connect(lambda: None)

    log.debug("Interfaz lista (oculta=%s)", hidden)
    return qapp.exec()
