"""Líneas de configuración de Hyprland para copiar y pegar.

Hyprland 0.55 cambió su configuración de hyprland.conf a hyprland.lua. La
versión 0.56 todavía acepta las dos (si no encuentra el .lua, vuelve al .conf),
pero en la rama de desarrollo ya se quitó el analizador antiguo, así que el
.conf tiene los días contados.

Aquí no se toca nada de Hyprland: solo se mira qué archivo tiene el usuario,
para enseñarle el texto que le sirve, y se genera ese texto. Copiarlo y
pegarlo sigue siendo cosa suya.
"""
import os
from pathlib import Path

LUA = "lua"
CONF = "conf"

# Combinación de teclas de ejemplo; el usuario la cambia por la que prefiera
MODIFIER = "SUPER"
KEY = "F10"

# Clase de la ventana en Wayland; sale de setDesktopFileName()
WINDOW_CLASS = "crosshair"


def config_dir():
    base = os.environ.get("XDG_CONFIG_HOME")
    base = Path(base) if base and os.path.isabs(base) else Path.home() / ".config"
    return base / "hypr"


def detect_flavour():
    """Qué formato de configuración usa Hyprland: "lua", "conf" o None si no
    hay ninguno de los dos.

    Se mira en el mismo orden que Hyprland: primero hyprland.lua y, si no está,
    hyprland.conf.
    """
    folder = config_dir()
    for flavour, name in ((LUA, "hyprland.lua"), (CONF, "hyprland.conf")):
        if (folder / name).is_file():
            return flavour
    return None


def lua_string(text):
    """Cadena de Lua con el texto dentro, eligiendo comillas que no choquen.

    Hace falta porque cuando el programa no está instalado la orden lleva
    comillas dobles: python "$HOME/.../run.py". En ese caso se usan corchetes
    largos de Lua, que admiten cualquier cosa dentro.
    """
    if '"' not in text and "\\" not in text:
        return f'"{text}"'
    level = ""
    while f"]{level}]" in text:
        level += "="
    return f"[{level}[{text}]{level}]"


def lua_lines(command):
    """Configuración en Lua, para Hyprland 0.55 o posterior.

    hl.exec_cmd pasa la orden por /bin/sh, igual que el exec-once de siempre,
    así que $HOME se expande y las comillas funcionan como en la terminal.
    """
    def cmd(flag):
        return lua_string(f"{command} {flag}")

    return "\n".join([
        "-- Crosshair",
        f'hl.on("hyprland.start", function() hl.exec_cmd({cmd("--hidden")}) end)',
        f'hl.bind("{MODIFIER} + {KEY}", hl.dsp.exec_cmd({cmd("--toggle")}))',
        f'hl.bind("{MODIFIER} + SHIFT + {KEY}", hl.dsp.exec_cmd({cmd("--next-profile")}))',
        f'hl.window_rule({{ name = "crosshair-float", '
        f'match = {{ class = "^({WINDOW_CLASS})$" }}, float = true }})',
    ])


def conf_lines(command):
    """Configuración clásica, para Hyprland 0.54 o anterior (y para 0.56 si
    todavía no has pasado tu configuración a Lua)."""
    return "\n".join([
        "# Crosshair",
        f"exec-once = {command} --hidden",
        f"bind = {MODIFIER}, {KEY}, exec, {command} --toggle",
        f"bind = {MODIFIER} SHIFT, {KEY}, exec, {command} --next-profile",
        f"windowrule = match:class ^({WINDOW_CLASS})$, float on",
    ])


def lines(flavour, command):
    return lua_lines(command) if flavour == LUA else conf_lines(command)


def file_name(flavour):
    return "hyprland.lua" if flavour == LUA else "hyprland.conf"


def explanation(flavour, detected):
    """Frase que acompaña a las líneas, según lo que se haya encontrado."""
    name = file_name(flavour)
    if detected is None:
        return (f"No encontré la configuración de Hyprland en {config_dir()}. "
                f"Estas líneas son para {name}.")
    if detected == flavour:
        return f"Encontré tu {name}. Pega estas líneas al final y cambia {MODIFIER}, {KEY} por tu combinación."
    return (f"Tu configuración es {file_name(detected)}, pero estas líneas son para "
            f"{name}. Pégalas solo si cambias de formato.")
