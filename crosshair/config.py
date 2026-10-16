"""Configuración de la mira: valores por defecto, validación y lectura y escritura.

Archivos en ~/.config/crosshair/:
  config.json    mira actual (la ventana de ajustes escribe, el overlay vigila)
  profiles.json  perfiles con nombre creados por el usuario
  images/        imágenes importadas como mira (siempre PNG)

Todo lo que entra se pasa por sanitize_config(), así que un archivo editado a
mano o de una versión anterior nunca deja el programa en un estado inválido.
"""
import copy
import json
import logging
import math
import os
from pathlib import Path

from .paths import (
    CONFIG_DIR,
    CONFIG_FILE,
    IMAGES_DIR,
    LEGACY_PROFILES_FILE,
    PROFILES_FILE,
)

log = logging.getLogger(__name__)

# Se guarda en los archivos para poder migrarlos en versiones futuras
SCHEMA_VERSION = 2

DEFAULTS = {
    "style": "cross",                # cross | tcross | x | dot | circle | image
    "color": [1.0, 0.1, 0.1, 1.0],   # RGBA, valores de 0 a 1
    "thickness": 2,                  # grosor de las líneas
    "arm": 10,                       # largo de cada brazo
    "gap": 4,                        # separación entre el centro y cada brazo
    "center_dot": True,              # punto central
    "dot_radius": 2,                 # radio del punto
    "circle_radius": 12,             # radio del círculo (estilo círculo)
    "outline": True,                 # contorno alrededor de la mira
    "outline_color": [0.0, 0.0, 0.0, 1.0],
    "outline_thickness": 1,          # grosor del contorno en píxeles
    "image": "",                     # nombre del archivo dentro de images/ (estilo imagen)
    "image_size": 64,                # lado mayor de la imagen en píxeles
    "image_opacity": 100,            # opacidad de la imagen, de 0 a 100
    "monitor": "",                   # conector del monitor (p. ej. "DP-1"); "" = automático
    "offset_x": 0,                   # desplazamiento horizontal (positivo: a la derecha)
    "offset_y": 0,                   # desplazamiento vertical (positivo: hacia arriba)
}

VALID_STYLES = ("cross", "tcross", "x", "dot", "circle", "image")

OFFSET_LIMIT = 500  # desplazamiento máximo de la mira, en píxeles, hacia cada lado

# Rango válido de cada valor numérico. Deben coincidir con los deslizadores de la interfaz.
LIMITS = {
    "thickness": (1, 8),
    "arm": (2, 40),
    "gap": (0, 20),
    "dot_radius": (1, 8),
    "circle_radius": (4, 50),
    "outline_thickness": (1, 4),
    "image_size": (16, 256),
    "image_opacity": (10, 100),
    "offset_x": (-OFFSET_LIMIT, OFFSET_LIMIT),
    "offset_y": (-OFFSET_LIMIT, OFFSET_LIMIT),
}

# Claves de la posición. No son parte del aspecto de la mira: los perfiles no
# las guardan, y elegir un perfil o restablecer la mira no las cambia.
PLACEMENT_KEYS = ("monitor", "offset_x", "offset_y")

COLOR_KEYS = ("color", "outline_color")
BOOL_KEYS = ("center_dot", "outline")

# Perfiles incluidos: solo guardan lo que cambia respecto a DEFAULTS
BUILTIN_PROFILES = {
    "Predeterminada": {},
    "Cruz con hueco": {
        "color": [1.0, 1.0, 1.0, 1.0], "thickness": 2, "arm": 8, "gap": 6,
        "center_dot": False,
    },
    "Cruz en T": {
        "style": "tcross", "color": [1.0, 1.0, 1.0, 1.0], "thickness": 2,
        "arm": 9, "gap": 5, "center_dot": False,
    },
    "Aspa fina": {
        "style": "x", "color": [1.0, 0.85, 0.2, 1.0], "thickness": 2,
        "arm": 9, "gap": 4, "center_dot": False,
    },
    "Punto verde": {
        "style": "dot", "color": [0.1, 1.0, 0.3, 1.0], "dot_radius": 3,
    },
    "Círculo cian": {
        "style": "circle", "color": [0.33, 1.0, 1.0, 1.0], "circle_radius": 12,
        "thickness": 2, "center_dot": True, "dot_radius": 1,
    },
}


def _is_number(value):
    """Número finito (los booleanos no cuentan, aunque en Python sean enteros)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def sanitize_config(data):
    """Devuelve una configuración completa y segura de usar: los valores por
    defecto más lo válido que haya en 'data'.

    Se ignoran las claves desconocidas, los valores con un tipo incorrecto se
    reemplazan por el predeterminado y los números se limitan a su rango. Si el
    estilo es "image" pero la imagen ya no existe, se vuelve a la cruz.
    """
    cfg = copy.deepcopy(DEFAULTS)
    if isinstance(data, dict):
        cfg.update({k: v for k, v in data.items() if k in DEFAULTS})

    if cfg["style"] not in VALID_STYLES:
        cfg["style"] = DEFAULTS["style"]

    for key, (low, high) in LIMITS.items():
        value = cfg[key]
        cfg[key] = max(low, min(high, int(round(value)))) if _is_number(value) else DEFAULTS[key]

    for key in BOOL_KEYS:
        if not isinstance(cfg[key], bool):
            cfg[key] = DEFAULTS[key]

    for key in COLOR_KEYS:
        value = cfg[key]
        if isinstance(value, (list, tuple)) and len(value) == 4 and all(_is_number(v) for v in value):
            cfg[key] = [min(1.0, max(0.0, float(v))) for v in value]
        else:
            cfg[key] = list(DEFAULTS[key])

    # Solo el nombre del archivo, nunca una ruta
    cfg["image"] = Path(cfg["image"]).name if isinstance(cfg["image"], str) else ""
    if cfg["style"] == "image" and image_path(cfg["image"]) is None:
        cfg["style"] = DEFAULTS["style"]

    monitor = cfg["monitor"]
    cfg["monitor"] = monitor.strip()[:64] if isinstance(monitor, str) else ""
    return cfg


def appearance(cfg):
    """Solo el aspecto de la mira: la configuración sin las claves de posición."""
    return {key: value for key, value in cfg.items() if key not in PLACEMENT_KEYS}


def placement(cfg):
    """Solo el monitor y el desplazamiento."""
    return {key: cfg[key] for key in PLACEMENT_KEYS}


def builtin_profile(name):
    """Aspecto completo de un perfil incluido."""
    return appearance(sanitize_config(BUILTIN_PROFILES[name]))


def profile_order(user_profiles):
    """Nombres de todos los perfiles, incluidos y del usuario, en el orden en
    que se muestran y en el que los recorre --next-profile."""
    return list(BUILTIN_PROFILES) + sorted(user_profiles, key=str.lower)


def profile_appearance(name, user_profiles):
    """Aspecto de un perfil por su nombre, o None si no existe. No distingue
    mayúsculas de minúsculas, para que escribirlo a mano sea más cómodo."""
    for candidate in profile_order(user_profiles):
        if candidate.casefold() == name.casefold():
            return (builtin_profile(candidate) if candidate in BUILTIN_PROFILES
                    else copy.deepcopy(user_profiles[candidate])), candidate
    return None


def next_profile_name(current, user_profiles):
    """Perfil siguiente al que coincide con 'current' (la mira actual), o el
    primero si no coincide con ninguno."""
    order = profile_order(user_profiles)
    if not order:
        return None
    look = appearance(current)
    for i, name in enumerate(order):
        found = profile_appearance(name, user_profiles)
        if found and found[0] == look:
            return order[(i + 1) % len(order)]
    return order[0]


def image_path(name):
    """Ruta de una imagen importada, o None si no hay nombre o el archivo no existe.
    Solo se usa el nombre del archivo, nunca rutas externas a images/."""
    if not name or not isinstance(name, str):
        return None
    path = IMAGES_DIR / Path(name).name
    return path if path.is_file() else None


def referenced_images(cfg, profiles):
    """Nombres de las imágenes que usan la mira actual y los perfiles del usuario."""
    names = set()
    for item in (cfg, *profiles.values()):
        image = item.get("image") if isinstance(item, dict) else None
        if isinstance(image, str) and image:
            names.add(Path(image).name)
    return names


def remove_unused_images(cfg, profiles):
    """Borra de images/ los PNG que ya no usa la mira actual ni ningún perfil.
    Son copias de las imágenes que el usuario importó, así que los originales
    no se tocan."""
    if not IMAGES_DIR.is_dir():
        return
    keep = referenced_images(cfg, profiles)
    for path in IMAGES_DIR.glob("*.png"):
        if path.is_file() and path.name not in keep:
            try:
                path.unlink()
            except OSError as error:
                log.warning("No se pudo borrar la imagen %s: %s", path.name, error)


# ---------------------------------------------------------------------------
# Lectura y escritura
# ---------------------------------------------------------------------------
def read_json(path):
    """Contenido de un archivo JSON, o None si falta o está dañado."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as error:
        log.warning("No se pudo leer %s: %s", path, error)
        return None


def write_json(path, data):
    """Escritura atómica: archivo temporal y luego reemplazo, así un corte de
    luz o un disco lleno no dejan el archivo a medias."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def _unwrap(raw, key):
    """Saca el contenido de un archivo con cabecera {"version": n, <key>: ...}.
    Los archivos de la versión anterior no la tienen y se leen tal cual."""
    if isinstance(raw, dict) and "version" in raw and key in raw:
        return raw[key]
    return raw


def load_config():
    """Lee la mira actual; si falta o está dañada, usa los valores por defecto."""
    return sanitize_config(_unwrap(read_json(CONFIG_FILE), "crosshair"))


def save_config(cfg):
    write_json(CONFIG_FILE, {"version": SCHEMA_VERSION, "crosshair": cfg})


def load_profiles():
    """Perfiles del usuario: {nombre: aspecto completo de la mira}.

    Si todavía no hay profiles.json pero existe el presets.json de versiones
    anteriores, se lee de ahí y se guarda con el nombre nuevo. El archivo viejo
    se conserva por si acaso.
    """
    raw = read_json(PROFILES_FILE)
    migrated = False
    if raw is None:
        raw = read_json(LEGACY_PROFILES_FILE)
        migrated = raw is not None

    data = _unwrap(raw, "profiles")
    if not isinstance(data, dict):
        return {}
    profiles = {name: appearance(sanitize_config(item)) for name, item in data.items()
                if isinstance(name, str) and isinstance(item, dict)}
    if migrated and profiles:
        log.info("Perfiles migrados de presets.json a profiles.json")
        try:
            save_profiles(profiles)
        except OSError as error:
            log.warning("No se pudieron migrar los perfiles: %s", error)
    return profiles


def save_profiles(profiles):
    write_json(PROFILES_FILE, {"version": SCHEMA_VERSION, "profiles": profiles})


def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
