"""Ventana del overlay: capa OVERLAY de wlr-layer-shell, transparente y sin
región de entrada, así que se ve encima de todo y los clics la atraviesan.

Vigila ~/.config/crosshair/config.json y se actualiza sola cuando cambia, sin
que la ventana de ajustes tenga que hablar con este proceso.

Pensado para Hyprland y cualquier otro compositor Wayland con wlr-layer-shell
(Sway, River, Niri, KDE Plasma). GNOME no lo implementa.
"""
import logging
import math
import signal
import sys
from ctypes import CDLL

# Requisito de gtk4-layer-shell: la biblioteca debe cargarse ANTES de importar Gtk.
CDLL("libgtk4-layer-shell.so")

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, Gio, Gtk  # noqa: E402
from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402

import cairo  # noqa: E402

from ..config import ensure_config_dir, load_config  # noqa: E402
from ..paths import APP_ID, CONFIG_DIR, CONFIG_FILE  # noqa: E402
from .render import ImageCache, draw  # noqa: E402

log = logging.getLogger(__name__)

NAMESPACE = "crosshair-overlay"
MIN_SIZE = 256  # lado mínimo de la ventana; debe caber la mira más grande
PAD_STEP = 64   # al desplazar la mira, la ventana crece en pasos de este tamaño


def window_size(cfg):
    """Tamaño de la ventana (ancho, alto) para que quepa la mira desplazada.

    La ventana no tiene anclas, así que el compositor siempre la centra en el
    monitor. Para mover la mira, la ventana se agranda y la mira se dibuja
    fuera de su centro. Crece a saltos para no pedir un tamaño nuevo con cada
    píxel que se mueve el deslizador.
    """
    def side(offset):
        return MIN_SIZE + 2 * PAD_STEP * math.ceil(abs(offset) / PAD_STEP)

    return side(cfg["offset_x"]), side(cfg["offset_y"])


def find_monitor(name):
    """Monitor conectado cuyo conector se llama 'name' (p. ej. "DP-1"), o None."""
    if not name:
        return None
    monitors = Gdk.Display.get_default().get_monitors()
    for i in range(monitors.get_n_items()):
        monitor = monitors.get_item(i)
        if monitor.get_connector() == name:
            return monitor
    return None


class Overlay:
    """Estado del overlay: la ventana, la configuración y los vigilantes.

    Hay que guardar los vigilantes en un atributo o Python los elimina y dejan
    de avisar de los cambios.
    """

    def __init__(self, app):
        self.cfg = load_config()
        self.images = ImageCache()
        self.file_monitor = None

        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_decorated(False)
        self.area = Gtk.DrawingArea()
        self.area.set_draw_func(self.on_draw)
        self.window.set_child(self.area)

        self._setup_layer_shell()
        self.apply_placement()
        self._watch_monitors()
        self._watch_config()
        self.window.present()

    # --- preparación --------------------------------------------------------
    def _setup_layer_shell(self):
        win = self.window
        LayerShell.init_for_window(win)
        LayerShell.set_namespace(win, NAMESPACE)
        LayerShell.set_layer(win, LayerShell.Layer.OVERLAY)
        LayerShell.set_keyboard_mode(win, LayerShell.KeyboardMode.NONE)
        # -1: la ventana se centra en el monitor completo. Con 0 (el valor por
        # defecto) se centraba en el espacio libre que dejan las barras, y una
        # barra lateral como la de Caelestia desplazaba la mira hacia un lado.
        LayerShell.set_exclusive_zone(win, -1)
        # La región de entrada solo se puede fijar cuando la superficie ya
        # existe. Al cambiar de monitor la ventana se recrea y esto se repite.
        win.connect("realize", self._make_click_through)

    @staticmethod
    def _make_click_through(window):
        """Región de entrada vacía: todos los clics pasan a la ventana de abajo."""
        surface = window.get_surface()
        if surface is not None:
            surface.set_input_region(cairo.Region())

    def _watch_monitors(self):
        """Vuelve a elegir el monitor cuando se conecta o desconecta uno. GTK
        agrega los monitores nuevos antes de conocer su nombre, así que también
        se espera a que llegue el nombre de cada uno."""
        def on_items_changed(model, position, _removed, added):
            for i in range(position, position + added):
                model.get_item(i).connect("notify::connector", lambda *_: self.apply_placement())
            self.apply_placement()

        Gdk.Display.get_default().get_monitors().connect("items-changed", on_items_changed)

    def _watch_config(self):
        """Vigila la carpeta de configuración y aplica los cambios de config.json."""
        ensure_config_dir()
        folder = Gio.File.new_for_path(str(CONFIG_DIR))
        self.file_monitor = folder.monitor_directory(Gio.FileMonitorFlags.NONE, None)

        def on_change(_monitor, file, other_file, _event):
            names = {f.get_basename() for f in (file, other_file) if f is not None}
            if CONFIG_FILE.name in names:
                self.cfg = load_config()
                log.debug("Configuración recargada: estilo %s", self.cfg["style"])
                self.apply_placement()
                self.area.queue_draw()

        self.file_monitor.connect("changed", on_change)

    # --- aplicación de los cambios -----------------------------------------
    def apply_placement(self):
        """Ajusta el tamaño de la ventana y el monitor a la configuración
        actual. Solo cambia lo necesario: cambiar de monitor recrea la ventana."""
        size = window_size(self.cfg)
        if tuple(self.window.get_default_size()) != size:
            self.window.set_default_size(*size)

        # Si el monitor elegido no está conectado (o es automático), decide el
        # compositor; Hyprland usa el monitor activo.
        target = find_monitor(self.cfg["monitor"])
        if LayerShell.get_monitor(self.window) != target:
            LayerShell.set_monitor(self.window, target)

    def on_draw(self, _area, cr, width, height):
        cx = width / 2 + self.cfg["offset_x"]
        cy = height / 2 - self.cfg["offset_y"]  # en pantalla, la Y crece hacia abajo
        draw(cr, self.cfg, cx, cy, self.images)


def on_activate(app):
    css = Gtk.CssProvider()
    css.load_from_string("window { background: transparent; }")  # requiere GTK >= 4.12
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
    app.overlay = Overlay(app)  # guardar la referencia o Python lo elimina


def main():
    logging.basicConfig(
        level=logging.DEBUG if "--debug" in sys.argv else logging.INFO,
        format="crosshair-overlay: %(message)s",
        stream=sys.stderr,
    )
    signal.signal(signal.SIGINT, signal.SIG_DFL)   # Ctrl+C cierra el programa
    signal.signal(signal.SIGTERM, signal.SIG_DFL)  # la ventana de ajustes lo cierra con SIGTERM
    app = Gtk.Application(application_id=f"{APP_ID}.Overlay")
    app.connect("activate", on_activate)
    return app.run(None)
