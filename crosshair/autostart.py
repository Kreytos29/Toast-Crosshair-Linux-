"""Inicio automático con la sesión.

Se hace con un archivo .desktop en ~/.config/autostart, que es el estándar y lo
respetan Hyprland (con dex o similar), KDE, GNOME y Xfce. En Hyprland también
sirve la línea exec-once de hyprland.conf; si el usuario ya la tiene puesta, no
debería activar además esta opción o el programa intentaría abrirse dos veces
(la segunda instancia termina sola, pero es trabajo de más).
"""
import logging

from . import __version__
from .paths import AUTOSTART_DIR, AUTOSTART_FILE

log = logging.getLogger(__name__)

TEMPLATE = """[Desktop Entry]
Type=Application
Version=1.0
Name=Crosshair
Comment=Mira para tus juegos
Exec={command} --hidden
Icon={icon}
Terminal=false
Categories=Game;Utility;
X-GNOME-Autostart-enabled=true
X-Crosshair-Version={version}
"""


def is_enabled():
    return AUTOSTART_FILE.is_file()


def set_enabled(enabled, command, icon):
    """Crea o borra el archivo de inicio automático. Devuelve True si quedó
    como se pidió."""
    try:
        if enabled:
            AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
            AUTOSTART_FILE.write_text(
                TEMPLATE.format(command=command, icon=icon, version=__version__), encoding="utf-8"
            )
        else:
            AUTOSTART_FILE.unlink(missing_ok=True)
        return True
    except OSError as error:
        log.warning("No se pudo cambiar el inicio automático: %s", error)
        return False
