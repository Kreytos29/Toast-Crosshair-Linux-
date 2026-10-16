"""Importación de imágenes para usarlas como mira.

Se acepta PNG y SVG, y siempre se guarda un PNG normalizado dentro de
images/. Así el overlay solo tiene que saber leer PNG y la mira se mantiene
nítida al cambiarle el tamaño.
"""
import logging

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter

try:
    from PyQt6.QtSvg import QSvgRenderer
except ImportError:  # sin qt6-svg solo se pueden importar PNG
    QSvgRenderer = None

from ..paths import IMAGES_DIR
from ..share import safe_stem

log = logging.getLogger(__name__)

MAX_SIDE = 256                      # lado mayor, en píxeles, de las imágenes importadas
MAX_BYTES = 20 * 1024 * 1024
FILE_FILTER = "Imágenes (*.png *.svg)"


class ImportError_(ValueError):
    """Mensaje listo para enseñar al usuario."""


def _render_svg(source):
    if QSvgRenderer is None:
        raise ImportError_("Para importar archivos SVG hace falta el paquete qt6-svg.")
    renderer = QSvgRenderer(str(source))
    if not renderer.isValid():
        raise ImportError_("No se pudo leer el archivo SVG.")
    size = renderer.defaultSize()
    w, h = size.width(), size.height()
    if w <= 0 or h <= 0:
        w = h = MAX_SIDE
    # Se dibuja siempre al tamaño máximo para que no pierda nitidez al agrandarla
    scale = MAX_SIDE / max(w, h)
    image = QImage(max(1, round(w * scale)), max(1, round(h * scale)), QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    return image


def _load_raster(source):
    image = QImage(str(source))
    if image.isNull():
        raise ImportError_("No se pudo leer la imagen. Usa un archivo PNG o SVG.")
    if max(image.width(), image.height()) > MAX_SIDE:
        image = image.scaled(
            MAX_SIDE, MAX_SIDE,
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation,
        )
    return image.convertToFormat(QImage.Format.Format_ARGB32)


def import_image(source):
    """Convierte un PNG o SVG en un PNG normalizado dentro de images/ y
    devuelve su nombre. Lanza ImportError_ con un mensaje claro si no se puede."""
    from pathlib import Path

    source = Path(source)
    try:
        if source.stat().st_size > MAX_BYTES:
            raise ImportError_("El archivo es demasiado grande (el máximo son 20 MB).")
    except OSError as error:
        raise ImportError_(f"No se pudo abrir el archivo: {error}") from error

    image = _render_svg(source) if source.suffix.lower() == ".svg" else _load_raster(source)

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    stem = safe_stem(source.stem)
    name, n = f"{stem}.png", 2
    while (IMAGES_DIR / name).exists():
        name, n = f"{stem}-{n}.png", n + 1
    if not image.save(str(IMAGES_DIR / name), "PNG"):
        raise ImportError_("No se pudo guardar la imagen en la carpeta de configuración.")
    log.debug("Imagen importada como %s", name)
    return name
