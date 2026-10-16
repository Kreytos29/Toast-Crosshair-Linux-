"""Iconos del programa, dibujados con código.

No hay archivos PNG: cada icono se dibuja de nuevo para el tamaño que se pide,
así los bordes quedan nítidos lo mismo a 16 px en la bandeja que a 256 px en un
lanzador. Las medidas van en fracciones del lado, de 0 a 1.

Hay dos iconos distintos a propósito:
  app_icon()   mira blanca sobre un cuadrado oscuro; para la ventana y el menú
               de aplicaciones, donde el icono se ve sobre cualquier fondo.
  tray_icon()  solo la mira, con un borde oscuro para que se lea igual en una
               barra clara que en una oscura. El punto central cambia de color
               según la mira esté activa o no.
"""
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

from ..config import sanitize_config
from ..geometry import shapes
from .painter import build_path
from .theme import COLORS

ICON_SIZES = (16, 22, 24, 32, 48, 64, 128, 256)

# Medidas de la mira del icono, en fracciones del lado
RING_R, RING_W = 0.265, 0.042
TICK_IN, TICK_OUT, TICK_W = 0.336, 0.422, 0.047
DOT_R = 0.052

DARK = QColor("#0d0e12")
LIGHT = QColor("#f2f4f8")


def _ticks(painter, size, width, color, cap=Qt.PenCapStyle.FlatCap):
    pen = QPen(color, width * size)
    pen.setCapStyle(cap)
    painter.setPen(pen)
    half = size / 2
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        painter.drawLine(
            QPointF(half + dx * TICK_IN * size, half + dy * TICK_IN * size),
            QPointF(half + dx * TICK_OUT * size, half + dy * TICK_OUT * size),
        )


def _ring(painter, size, width, color):
    painter.setPen(QPen(color, width * size))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    r = RING_R * size
    painter.drawEllipse(QPointF(size / 2, size / 2), r, r)


def _dot(painter, size, radius, color):
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(QPointF(size / 2, size / 2), radius * size, radius * size)


def draw_app_icon(painter, size):
    """Mira blanca con el punto central rojo, sobre un cuadrado redondeado.
    Por debajo de 24 px se quitan las marcas exteriores: a ese tamaño no se
    distinguirían y solo ensucian la silueta."""
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    inset, corner = 0.031 * size, 0.22 * size
    box = QRectF(inset, inset, size - 2 * inset, size - 2 * inset)
    gradient = QLinearGradient(0, inset, 0, size - inset)
    gradient.setColorAt(0.0, QColor("#2a2e38"))
    gradient.setColorAt(1.0, QColor("#111318"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(gradient)
    painter.drawRoundedRect(box, corner, corner)
    # Filo claro apenas visible: despega el icono de un fondo oscuro
    painter.setPen(QPen(QColor(255, 255, 255, 20), max(1.0, 0.012 * size)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(box, corner, corner)

    detailed = size >= 32
    _ring(painter, size, RING_W if detailed else 0.072, LIGHT)
    if detailed:
        _ticks(painter, size, TICK_W, LIGHT)
    _dot(painter, size, DOT_R if detailed else 0.072, QColor(COLORS["accent"]))


def draw_tray_icon(painter, size, active):
    """Mira sola, con un halo oscuro para que se lea sobre cualquier barra.
    El punto central es rojo con la mira activa y gris cuando está apagada."""
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    detailed = size >= 20
    # En los tamaños pequeños todo se adelgaza un poco o el dibujo se empasta
    halo = 0.055 if detailed else 0.042
    dot = 0.09 if detailed else 0.072

    # 1) silueta oscura, un poco más gruesa; hace de borde
    _ring(painter, size, 0.085 + halo, DARK)
    if detailed:
        _ticks(painter, size, 0.075 + halo, DARK, Qt.PenCapStyle.RoundCap)
    _dot(painter, size, dot + halo / 2, DARK)

    # 2) la mira encima
    _ring(painter, size, 0.085, LIGHT)
    if detailed:
        _ticks(painter, size, 0.075, LIGHT, Qt.PenCapStyle.RoundCap)
    _dot(painter, size, dot, QColor(COLORS["accent"]) if active else QColor("#9aa1ad"))


def _build(draw, sizes=ICON_SIZES):
    icon = QIcon()
    for size in sizes:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        draw(painter, size)
        painter.end()
        icon.addPixmap(pixmap)
    return icon


_cache = {}


def app_icon():
    if "app" not in _cache:
        _cache["app"] = _build(draw_app_icon)
    return _cache["app"]


def tray_icon(active):
    key = f"tray-{active}"
    if key not in _cache:
        _cache[key] = _build(
            lambda p, s, a=active: draw_tray_icon(p, s, a), sizes=(16, 22, 24, 32, 48, 64)
        )
    return _cache[key]


# ---------------------------------------------------------------------------
# Miniaturas de cada estilo, para los botones del selector
# ---------------------------------------------------------------------------
# Las miniaturas se dibujan en una caja de referencia de 32 px y luego se
# escalan, así todas se ven del mismo tamaño sea cual sea el botón.
GLYPH_BOX = 32
GLYPH_CONFIGS = {
    "cross": {"thickness": 3, "arm": 8, "gap": 4, "center_dot": False},
    "tcross": {"thickness": 3, "arm": 8, "gap": 4, "center_dot": False},
    "x": {"thickness": 3, "arm": 8, "gap": 3, "center_dot": False},
    "dot": {"dot_radius": 6},
    "circle": {"circle_radius": 9, "thickness": 3, "center_dot": False},
}


def _draw_image_glyph(painter, color):
    """Dibujo genérico de "imagen": un marco con una montaña y un sol."""
    painter.setPen(QPen(color, 2.2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(QRectF(-12, -10, 24, 20), 3.5, 3.5)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(QPointF(-4.8, -4.0), 2.4, 2.4)
    mountain = QPainterPath()
    mountain.moveTo(-9.8, 8.0)
    mountain.lineTo(-2.2, -0.8)
    mountain.lineTo(3.0, 4.6)
    mountain.lineTo(6.2, 1.4)
    mountain.lineTo(9.8, 8.0)
    mountain.closeSubpath()
    painter.drawPath(mountain)


def style_glyph(style, size, color):
    """Miniatura de un estilo de mira, para el botón del selector."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.translate(size / 2, size / 2)
    painter.scale(size / GLYPH_BOX, size / GLYPH_BOX)
    if style == "image":
        _draw_image_glyph(painter, color)
    else:
        cfg = sanitize_config({"style": style, **GLYPH_CONFIGS.get(style, {})})
        painter.fillPath(build_path(shapes(cfg, 0)), color)
    painter.end()
    return pixmap
