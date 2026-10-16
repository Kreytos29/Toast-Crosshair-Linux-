"""Controles propios de la ventana de ajustes.

Qt no trae interruptores, muestras de color con transparencia ni nada parecido
al mapa de posición, así que se dibujan a mano para que todo combine con el
tema oscuro.
"""
from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QFrame,
    QLabel,
    QPushButton,
    QWidget,
)

from ..config import OFFSET_LIMIT
from ..geometry import radius as crosshair_radius
from .painter import render, to_qcolor
from .theme import COLORS, METRICS

# Fondos de la vista previa; se cambian con un clic para comprobar que la mira
# se distingue sobre claro, sobre oscuro y sobre un color parecido al suyo.
PREVIEW_BACKGROUNDS = [
    ("oscuro", QColor(26, 28, 34)),
    ("claro", QColor(226, 229, 234)),
    ("hierba", QColor(58, 102, 62)),
    ("gris medio", QColor(124, 126, 132)),
    ("cuadros", None),  # tablero de ajedrez, para ver la transparencia
]


def label(text, name="rowLabel"):
    widget = QLabel(text)
    widget.setObjectName(name)
    return widget


def rule():
    """Separador de 1 píxel."""
    line = QFrame()
    line.setObjectName("rule")
    line.setFrameShape(QFrame.Shape.HLine)
    return line


def checkerboard(painter, rect, light="#c8c8c8", dark="#8c8c8c", cell=8):
    for iy in range(int(rect.top()), int(rect.bottom()) + cell, cell):
        for ix in range(int(rect.left()), int(rect.right()) + cell, cell):
            pale = ((ix // cell) + (iy // cell)) % 2 == 0
            painter.fillRect(
                QRectF(ix, iy, cell, cell).intersected(rect), QColor(light if pale else dark)
            )


def color_swatch(rgba, width=24, height=16):
    """Muestra de color con un tablero detrás, para que se note la transparencia."""
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(0, 0, width, height), 4, 4)
    p.setClipPath(clip)
    checkerboard(p, QRectF(0, 0, width, height), cell=4)
    p.fillRect(QRectF(0, 0, width, height), to_qcolor(rgba))
    p.setClipping(False)
    p.setPen(QColor(255, 255, 255, 46))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(0.5, 0.5, width - 1, height - 1), 4, 4)
    p.end()
    return pixmap


class Combo(QComboBox):
    """Desplegable con la flecha dibujada a mano, porque el tema oscuro no usa
    la del sistema. Su ancho no depende del texto de las opciones: la ventana
    tiene tamaño fijo y un nombre largo no debe ensancharla."""

    def __init__(self):
        super().__init__()
        self.setObjectName("combo")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(8)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(COLORS["text2"]), 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        x, y = self.width() - 16, self.height() / 2
        p.drawPolyline([QPointF(x - 4, y - 2), QPointF(x, y + 2), QPointF(x + 4, y - 2)])
        p.end()


class Switch(QPushButton):
    """Interruptor de encendido y apagado. Es un botón con dos estados, así que
    se usa igual que una casilla de verificación."""

    TRACK_W, TRACK_H = 34, 19

    def __init__(self):
        super().__init__()
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(self.TRACK_W, self.TRACK_H + 4)
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        top = (self.height() - self.TRACK_H) / 2
        enabled, on = self.isEnabled(), self.isChecked()

        track = QColor(COLORS["accent"] if on else COLORS["track"])
        if not enabled:
            track.setAlphaF(0.4)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(
            QRectF(0, top, self.TRACK_W, self.TRACK_H), self.TRACK_H / 2, self.TRACK_H / 2
        )

        knob = self.TRACK_H - 5
        x = self.TRACK_W - 2.5 - knob if on else 2.5
        p.setBrush(QColor("#ffffff" if enabled else COLORS["muted"]))
        p.drawEllipse(QRectF(x, top + 2.5, knob, knob))
        p.end()


class ColorButton(QPushButton):
    """Botón que muestra el color actual y abre el selector al pulsarlo."""

    color_changed = pyqtSignal(list)

    def __init__(self, rgba, title):
        super().__init__()
        self.setObjectName("colorBtn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.title = title
        self.rgba = list(rgba)
        self.clicked.connect(self._pick)
        self._refresh()

    def set_color(self, rgba):
        self.rgba = list(rgba)
        self._refresh()

    def _refresh(self):
        color = to_qcolor(self.rgba)
        swatch = color_swatch(self.rgba)
        self.setIcon(QIcon(swatch))
        self.setIconSize(swatch.size())
        self.setText(f"  {color.name().upper()}   {round(color.alphaF() * 100)} %")

    def _pick(self):
        chosen = QColorDialog.getColor(
            to_qcolor(self.rgba), self, self.title, QColorDialog.ColorDialogOption.ShowAlphaChannel
        )
        if chosen.isValid():
            self.rgba = [chosen.redF(), chosen.greenF(), chosen.blueF(), chosen.alphaF()]
            self._refresh()
            self.color_changed.emit(self.rgba)


class Preview(QWidget):
    """Vista previa ampliada de la mira. Un clic cambia el fondo."""

    SIZE = METRICS["rail"]
    RADIUS = METRICS["radius_lg"]

    background_changed = pyqtSignal(str)

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.bg_index = 0
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Clic para cambiar el fondo")

    @staticmethod
    def zoom_for(cfg):
        """x3 normalmente; se reduce cuando la mira es grande, para que quepa
        entera con un margen."""
        usable = Preview.SIZE - 48
        extent = max(8.0, crosshair_radius(cfg, cfg["outline_thickness"] if cfg["outline"] else 0) * 2)
        return max(1.0, min(3.0, round(usable / extent * 2) / 2))

    @property
    def zoom(self):
        return self.zoom_for(self.cfg)

    def set_config(self, cfg):
        self.cfg = cfg
        self.update()

    def mousePressEvent(self, _event):
        self.bg_index = (self.bg_index + 1) % len(PREVIEW_BACKGROUNDS)
        self.update()
        self.background_changed.emit(PREVIEW_BACKGROUNDS[self.bg_index][0])

    def paintEvent(self, _event):
        w, h = self.width(), self.height()
        name, bg = PREVIEW_BACKGROUNDS[self.bg_index]

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()), self.RADIUS, self.RADIUS)
        p.setClipPath(clip)

        if bg is None:
            checkerboard(p, QRectF(self.rect()), "#b4b4b4", "#8e8e8e", 12)
            pale = True
        else:
            p.fillRect(self.rect(), bg)
            pale = bg.lightness() > 128

        # Guías del centro: ayudan a ver si la mira está bien centrada
        guide = QColor(0, 0, 0, 28) if pale else QColor(255, 255, 255, 26)
        p.setPen(QPen(guide, 1))
        p.drawLine(QPointF(w / 2, 10), QPointF(w / 2, h - 10))
        p.drawLine(QPointF(10, h / 2), QPointF(w - 10, h / 2))

        # La mira se dibuja antes en una capa transparente (respetando la escala
        # de pantalla) porque el contorno necesita vaciar el interior
        dpr = self.devicePixelRatioF()
        layer = QPixmap(int(w * dpr), int(h * dpr))
        layer.setDevicePixelRatio(dpr)
        layer.fill(Qt.GlobalColor.transparent)
        lp = QPainter(layer)
        lp.translate(w / 2, h / 2)
        lp.scale(self.zoom, self.zoom)
        render(lp, self.cfg)
        lp.end()
        p.drawPixmap(0, 0, layer)

        # Puntos que indican el fondo actual
        dot = QColor(0, 0, 0, 200) if pale else QColor(255, 255, 255, 210)
        faint = QColor(dot)
        faint.setAlpha(60)
        count = len(PREVIEW_BACKGROUNDS)
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(count):
            p.setBrush(dot if i == self.bg_index else faint)
            p.drawEllipse(QPointF(w / 2 + (i - (count - 1) / 2) * 12, h - 14), 2.5, 2.5)

        p.setClipping(False)
        p.setPen(QPen(QColor(COLORS["line"]), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), self.RADIUS, self.RADIUS)
        p.end()


class PositionPad(QWidget):
    """Mapa del monitor: muestra dónde queda la mira y permite arrastrarla.

    El rectángulo interior es la pantalla, a escala. La zona marcada con línea
    discontinua es hasta dónde llega el desplazamiento máximo.
    """

    BOX_W, BOX_H = METRICS["panel_w"] - 32, 184
    moved = pyqtSignal(int, int)  # offset_x, offset_y en píxeles de pantalla

    def __init__(self):
        super().__init__()
        self.offset = (0, 0)
        self.screen_size = (1920, 1080)
        self.setFixedSize(self.BOX_W, self.BOX_H)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setToolTip("Arrastra para mover la mira")

    def set_state(self, offset, screen_size=None):
        self.offset = offset
        if screen_size and screen_size[0] > 0 and screen_size[1] > 0:
            self.screen_size = screen_size
        self.update()

    # --- conversión entre píxeles de pantalla y del mapa --------------------
    def _screen_rect(self):
        """Rectángulo del mapa que representa la pantalla, con su proporción."""
        margin = 10
        aw, ah = self.BOX_W - 2 * margin, self.BOX_H - 2 * margin
        sw, sh = self.screen_size
        scale = min(aw / sw, ah / sh)
        w, h = sw * scale, sh * scale
        return QRectF((self.BOX_W - w) / 2, (self.BOX_H - h) / 2, w, h), scale

    def mousePressEvent(self, event):
        self._apply(event.position())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._apply(event.position())

    def _apply(self, pos):
        rect, scale = self._screen_rect()
        x = (pos.x() - rect.center().x()) / scale
        y = (rect.center().y() - pos.y()) / scale  # la Y de la configuración crece hacia arriba
        clamp = lambda v: max(-OFFSET_LIMIT, min(OFFSET_LIMIT, int(round(v))))
        self.moved.emit(clamp(x), clamp(y))

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect, scale = self._screen_rect()

        # La pantalla
        p.setPen(QPen(QColor(COLORS["line"]), 1))
        p.setBrush(QColor(COLORS["field"]))
        p.drawRoundedRect(rect, 6, 6)

        # Zona a la que llega el desplazamiento, solo si se nota dentro de la pantalla
        limit = QRectF(0, 0, 2 * OFFSET_LIMIT * scale, 2 * OFFSET_LIMIT * scale)
        limit.moveCenter(rect.center())
        if limit.width() < rect.width() - 6 or limit.height() < rect.height() - 6:
            p.setPen(QPen(QColor(COLORS["muted"]), 1, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(limit.intersected(rect.adjusted(1, 1, -1, -1)))

        # Guías del centro
        p.setPen(QPen(QColor(COLORS["track"]), 1))
        p.drawLine(QPointF(rect.center().x(), rect.top() + 5), QPointF(rect.center().x(), rect.bottom() - 5))
        p.drawLine(QPointF(rect.left() + 5, rect.center().y()), QPointF(rect.right() - 5, rect.center().y()))

        # Resolución del monitor, de fondo
        p.setPen(QColor(COLORS["muted"]))
        font = p.font()
        font.setPointSizeF(max(7.0, font.pointSizeF() - 2))
        p.setFont(font)
        p.drawText(rect.adjusted(8, 4, -8, -4), int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft),
                   f"{self.screen_size[0]} × {self.screen_size[1]}")

        # La mira
        cx = rect.center().x() + self.offset[0] * scale
        cy = rect.center().y() - self.offset[1] * scale
        accent = QColor(COLORS["accent"])
        p.setPen(QPen(accent, 1.6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), 7, 7)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p.drawLine(QPointF(cx + dx * 9, cy + dy * 9), QPointF(cx + dx * 13, cy + dy * 13))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(accent)
        p.drawEllipse(QPointF(cx, cy), 2.2, 2.2)
        p.end()


class StyleSelector(QWidget):
    """Fila de botones con una miniatura de cada estilo de mira."""

    BUTTON_H = 40
    selected = pyqtSignal(str)

    def __init__(self, styles):
        super().__init__()
        from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout

        self.buttons = {}
        group = QButtonGroup(self)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        for value, name in styles:
            button = QPushButton()
            button.setObjectName("styleBtn")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(name)
            button.setFixedHeight(self.BUTTON_H)
            button.setIcon(self._glyphs(value))
            button.setIconSize(QSize(26, 26))
            button.clicked.connect(lambda _checked=False, v=value: self.selected.emit(v))
            group.addButton(button)
            row.addWidget(button, 1)
            self.buttons[value] = button

    @staticmethod
    def _glyphs(style):
        """Miniatura con dos versiones: apagada y, cuando el botón está
        marcado, en el color de marca."""
        from .icons import style_glyph

        icon = QIcon()
        icon.addPixmap(style_glyph(style, 26, QColor(COLORS["text2"])), QIcon.Mode.Normal, QIcon.State.Off)
        icon.addPixmap(style_glyph(style, 26, QColor(COLORS["text"])), QIcon.Mode.Active, QIcon.State.Off)
        icon.addPixmap(style_glyph(style, 26, QColor(COLORS["accent"])), QIcon.Mode.Normal, QIcon.State.On)
        icon.addPixmap(style_glyph(style, 26, QColor(COLORS["accent"])), QIcon.Mode.Active, QIcon.State.On)
        return icon

    def set_style(self, value):
        button = self.buttons.get(value)
        if button is not None:
            button.setChecked(True)
