"""Dibujo de la mira con Cairo, a partir de las formas de crosshair.geometry."""
import logging
import math

import cairo

from ..config import image_path
from ..geometry import Disc, Polygon, Ring, shapes

log = logging.getLogger(__name__)

TWO_PI = 2 * math.pi


class ImageCache:
    """Guarda la imagen de la mira ya cargada y la recarga solo si el archivo
    cambia, para no leer el PNG en cada redibujado."""

    def __init__(self):
        self._key = None
        self._surface = None

    def get(self, name):
        path = image_path(name)
        if path is None:
            return None
        try:
            key = (str(path), path.stat().st_mtime_ns)
        except OSError:
            return None
        if self._key != key:
            try:
                self._surface = cairo.ImageSurface.create_from_png(str(path))
            except Exception as error:  # archivo dañado o no es un PNG válido
                log.warning("No se pudo cargar la imagen %s: %s", path.name, error)
                self._surface = None
            self._key = key
        return self._surface


def add_shapes(cr, items, dx, dy):
    """Agrega las formas a la ruta actual, trasladadas a (dx, dy)."""
    for item in items:
        if isinstance(item, Polygon):
            (x0, y0), *rest = item.points
            cr.move_to(dx + x0, dy + y0)
            for x, y in rest:
                cr.line_to(dx + x, dy + y)
            cr.close_path()
        elif isinstance(item, Disc):
            cr.new_sub_path()
            cr.arc(dx + item.cx, dy + item.cy, item.r, 0, TWO_PI)
        elif isinstance(item, Ring):
            cr.new_sub_path()
            cr.arc(dx + item.cx, dy + item.cy, item.outer, 0, TWO_PI)
            if item.inner > 0:
                # Sentido contrario al círculo exterior para que quede el hueco
                cr.new_sub_path()
                cr.arc_negative(dx + item.cx, dy + item.cy, item.inner, 0, -TWO_PI)


def draw_image(cr, cfg, cx, cy, surface):
    """Dibuja la imagen centrada, con su lado mayor igual a image_size."""
    if surface is None:
        return
    w, h = surface.get_width(), surface.get_height()
    scale = max(1, cfg["image_size"]) / max(w, h)
    cr.save()
    # Posición redondeada a píxeles enteros para que la imagen quede nítida
    cr.translate(round(cx - w * scale / 2), round(cy - h * scale / 2))
    cr.scale(scale, scale)
    cr.set_source_surface(surface, 0, 0)
    cr.get_source().set_filter(cairo.FILTER_BEST)
    cr.paint_with_alpha(max(0, min(100, cfg["image_opacity"])) / 100)
    cr.restore()


def draw(cr, cfg, cx, cy, image_cache):
    """Dibuja el contorno (si está activo) y luego la mira, centrados en (cx, cy)."""
    cr.set_fill_rule(cairo.FILL_RULE_WINDING)

    if cfg["style"] == "image":
        draw_image(cr, cfg, cx, cy, image_cache.get(cfg["image"]))
        return

    body = shapes(cfg, 0)

    if cfg["outline"]:
        # 1) contorno: la mira expandida
        cr.new_path()
        add_shapes(cr, shapes(cfg, cfg["outline_thickness"]), cx, cy)
        cr.set_source_rgba(*cfg["outline_color"])
        cr.fill()
        # 2) se vacía el interior para que un color semitransparente no se
        #    mezcle con el contorno que queda debajo
        cr.new_path()
        add_shapes(cr, body, cx, cy)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.fill()
        cr.set_operator(cairo.OPERATOR_OVER)

    # 3) la mira
    cr.new_path()
    add_shapes(cr, body, cx, cy)
    cr.set_source_rgba(*cfg["color"])
    cr.fill()
