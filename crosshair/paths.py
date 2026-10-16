"""Rutas de los archivos del programa, según el estándar XDG."""
import os
from pathlib import Path

APP_ID = "dev.kreytos.Crosshair"  # identificador de D-Bus y de la aplicación GTK del overlay
APP_NAME = "crosshair"
# Nombre del archivo .desktop. En Wayland es también la clase de la ventana, así
# que una regla como «windowrule = match:class ^(crosshair)$» depende de él.
DESKTOP_NAME = "crosshair"


def _base(variable, default):
    value = os.environ.get(variable)
    return Path(value) if value and os.path.isabs(value) else Path.home() / default


CONFIG_DIR = _base("XDG_CONFIG_HOME", ".config") / APP_NAME
CONFIG_FILE = CONFIG_DIR / "config.json"
PROFILES_FILE = CONFIG_DIR / "profiles.json"
LEGACY_PROFILES_FILE = CONFIG_DIR / "presets.json"  # nombre anterior, se migra al nuevo
IMAGES_DIR = CONFIG_DIR / "images"

AUTOSTART_DIR = _base("XDG_CONFIG_HOME", ".config") / "autostart"
AUTOSTART_FILE = AUTOSTART_DIR / f"{DESKTOP_NAME}.desktop"


def runtime_socket():
    """Socket de la instancia en ejecución (uno por usuario)."""
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime or not os.path.isdir(runtime):
        runtime = "/tmp"
    return os.path.join(runtime, f"{APP_NAME}-{os.getuid()}.sock")


def project_root():
    """Carpeta que contiene al paquete. Se usa para ejecutar el overlay y para
    construir la línea del atajo de teclado cuando el programa no está instalado."""
    return Path(__file__).resolve().parent.parent
