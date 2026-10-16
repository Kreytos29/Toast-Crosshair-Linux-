"""Dibujo de la mira con QPainter, a partir de las formas de crosshair.geometry.

Es el equivalente de crosshair.overlay.render pero para la vista previa. Como
los dos piden las formas al mismo módulo, la vista previa no puede quedar
distinta de lo que se ve en pantalla.
"""
import logging

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath

from ..config import image_path
from ..geometry import Disc, Polygon, Ring, shapes

log = logging.getLogger(__name__)


def to_qcolor(rgba):
    r, g, b, a = (min(1.0, max(0.0, float(v))) for v in rgba)
    return QColor.fromRgbF(r, g, b, a)


def build_path(items):
    """QPainterPath con las formas de la mira, centradas en el origen."""
    path = QPainterPath()
    path.setFillRule(Qt.FillRule.WindingFill)
    for item in items:
        if isinstance(item, Polygon):
            (x0, y0), *rest = item.points
            path.moveTo(x0, y0)
            for x, y in rest:
                path.lineTo(x, y)
            path.closeSubpath()
        elif isinstance(item, Disc):
            path.addEllipse(QPointF(item.cx, item.cy), item.r, item.r)
        elif isinstance(item, Ring):
            path.addEllipse(QPointF(item.cx, item.cy), item.outer, item.outer)
            if item.inner > 0:
                # Sentido contrario al círculo exterior para que quede el hueco
                inner = item.inner
                path.moveTo(item.cx + inner, item.cy)
                path.arcTo(QRectF(item.cx - inner, item.cy - inner, 2 * inner, 2 * inner), 0, 360)
                path.closeSubpath()
    return path


class ImageCache:
    """Imagen de la mira ya cargada; se recarga solo si el archivo cambia."""

    def __init__(self):
        self._key = None
        self._image = None

    def get(self, name):
        path = image_path(name)
        if path is None:
            return None
        try:
            key = (str(path), path.stat().st_mtime_ns)
        except OSError:
            return None
        if self._key != key:
            image = QImage(str(path))
            if image.isNull():
                log.warning("No se pudo cargar la imagen %s", path.name)
                image = None
            self._key, self._image = key, image
        return self._image


_images = ImageCache()


def render(p, cfg):
    """Dibuja la mira en el origen del painter. El destino debe ser transparente,
    porque el contorno se hace vaciando el interior de la silueta."""
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    if cfg["style"] == "image":
        image = _images.get(cfg["image"])
        if image is not None:
            scale = max(1, cfg["image_size"]) / max(image.width(), image.height())
            w, h = image.width() * scale, image.height() * scale
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            p.setOpacity(max(0, min(100, cfg["image_opacity"])) / 100)
            p.drawImage(QRectF(-w / 2, -h / 2, w, h), image)
            p.setOpacity(1.0)
        return

    body = build_path(shapes(cfg, 0))

    if cfg["outline"]:
        p.fillPath(build_path(shapes(cfg, cfg["outline_thickness"])), to_qcolor(cfg["outline_color"]))
        # Se vacía el interior para que un color semitransparente no se mezcle
        # con el contorno que queda debajo
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        p.fillPath(body, QColor(0, 0, 0, 255))
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

    p.fillPath(body, to_qcolor(cfg["color"]))
