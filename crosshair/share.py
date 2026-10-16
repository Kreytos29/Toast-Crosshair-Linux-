"""Importar y exportar una mira como archivo, para copiarla a otro equipo o
pasársela a alguien.

El archivo es un JSON con la mira dentro. Si la mira es una imagen, el PNG va
incluido en el mismo archivo (codificado en base64), así no hay que mandar dos
archivos ni se rompe el perfil al abrirlo en otro equipo.
"""
import base64
import binascii
import json
import re
from pathlib import Path

from .config import SCHEMA_VERSION, appearance, image_path, sanitize_config
from .paths import IMAGES_DIR

FILE_SUFFIX = ".crosshair.json"
FILE_FILTER = "Mira de Crosshair (*.json)"
MAX_IMAGE_BYTES = 4 * 1024 * 1024  # un PNG de 256 px nunca llega ni de lejos


class ShareError(Exception):
    """Mensaje listo para enseñar al usuario."""


def safe_stem(text, fallback="mira"):
    """Nombre de archivo sin caracteres raros ni rutas."""
    stem = re.sub(r"[^\w\-]+", "-", Path(str(text)).stem).strip("-")[:40]
    return stem or fallback


def export_data(cfg, name):
    """Contenido del archivo de exportación para la mira actual."""
    data = {
        "app": "crosshair",
        "version": SCHEMA_VERSION,
        "name": str(name)[:40],
        "crosshair": appearance(cfg),
    }
    if cfg["style"] == "image":
        path = image_path(cfg["image"])
        if path is None:
            raise ShareError("La imagen de la mira ya no está en la carpeta de configuración.")
        raw = path.read_bytes()
        if len(raw) > MAX_IMAGE_BYTES:
            raise ShareError("La imagen es demasiado grande para exportarla.")
        data["image"] = {"name": path.name, "png_base64": base64.b64encode(raw).decode("ascii")}
    return data


def export_to(path, cfg, name):
    """Guarda la mira en un archivo. Devuelve la ruta usada."""
    path = Path(path)
    if path.suffix.lower() != ".json":
        path = path.with_name(path.name + ".json")
    try:
        path.write_text(json.dumps(export_data(cfg, name), indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    except OSError as error:
        raise ShareError(f"No se pudo guardar el archivo: {error}") from error
    return path


def _restore_image(block):
    """Guarda el PNG incluido en images/ y devuelve su nombre."""
    if not isinstance(block, dict):
        return ""
    try:
        raw = base64.b64decode(block.get("png_base64", ""), validate=True)
    except (binascii.Error, ValueError) as error:
        raise ShareError("La imagen incluida en el archivo está dañada.") from error
    if not raw or len(raw) > MAX_IMAGE_BYTES:
        raise ShareError("La imagen incluida en el archivo no es válida.")
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ShareError("La imagen incluida en el archivo no es un PNG.")

    stem = safe_stem(block.get("name", "mira"))
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    name, n = f"{stem}.png", 2
    while (IMAGES_DIR / name).exists():
        name, n = f"{stem}-{n}.png", n + 1
    try:
        (IMAGES_DIR / name).write_bytes(raw)
    except OSError as error:
        raise ShareError(f"No se pudo guardar la imagen: {error}") from error
    return name


def import_from(path):
    """Lee un archivo exportado. Devuelve (aspecto de la mira, nombre sugerido).
    Lanza ShareError con un mensaje claro si el archivo no sirve."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as error:
        raise ShareError(f"No se pudo abrir el archivo: {error}") from error
    except ValueError as error:
        raise ShareError("El archivo no es un JSON válido.") from error

    if not isinstance(raw, dict) or not isinstance(raw.get("crosshair"), dict):
        raise ShareError("El archivo no contiene ninguna mira.")

    data = dict(raw["crosshair"])
    if "image" in raw:
        data["image"] = _restore_image(raw["image"])
    # sanitize_config vuelve a la cruz si el estilo es imagen y el PNG no existe
    look = appearance(sanitize_config(data))
    name = raw.get("name")
    return look, (str(name)[:40] if isinstance(name, str) and name.strip() else "Mira importada")
