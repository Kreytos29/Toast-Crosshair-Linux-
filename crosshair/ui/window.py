"""Ventana de ajustes.

A la izquierda, la vista previa y los perfiles; a la derecha, tres pestañas con
los ajustes. Todo lo que se toca aquí se guarda en config.json, y el overlay se
entera solo porque vigila el archivo: este proceso nunca le habla directamente.
"""
import copy
import logging
import os
import shutil
import sys
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QButtonGroup,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLayout,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from .. import __author__, __version__, autostart, hyprland, share
from ..config import (
    BUILTIN_PROFILES,
    DEFAULTS,
    LIMITS,
    OFFSET_LIMIT,
    appearance,
    builtin_profile,
    ensure_config_dir,
    image_path,
    load_config,
    load_profiles,
    placement,
    remove_unused_images,
    save_config,
    save_profiles,
)
from ..paths import CONFIG_DIR, DESKTOP_NAME, project_root
from .icons import app_icon
from .images import ImportError_, import_image
from .images import FILE_FILTER as IMAGE_FILTER
from .theme import COLORS, METRICS, STYLESHEET
from .widgets import (
    PREVIEW_BACKGROUNDS,
    ColorButton,
    Combo,
    PositionPad,
    Preview,
    StyleSelector,
    Switch,
    label,
    rule,
)

log = logging.getLogger(__name__)

STYLES = [
    ("cross", "Cruz"),
    ("tcross", "Cruz en T"),
    ("x", "Aspa"),
    ("dot", "Punto"),
    ("circle", "Círculo"),
    ("image", "Imagen"),
]
STYLE_NAMES = dict(STYLES)
CUSTOM_LABEL = "Personalizado"  # cuando la mira no coincide con ningún perfil


# ---------------------------------------------------------------------------
# Ayudantes de construcción
# ---------------------------------------------------------------------------
class Form(QWidget):
    """Columna de filas «etiqueta + control», con todas las etiquetas del mismo
    ancho para que los controles empiecen en la misma columna."""

    def __init__(self):
        super().__init__()
        self._form = QFormLayout(self)
        self._form.setContentsMargins(0, 0, 0, 0)
        self._form.setHorizontalSpacing(12)
        self._form.setVerticalSpacing(5)
        self._form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.rows = {}

    def add(self, text, widget, key=None, tip=None):
        text_label = label(text)
        text_label.setFixedWidth(METRICS["label_w"])
        text_label.setMinimumHeight(METRICS["row_h"])
        if tip:
            text_label.setToolTip(tip)
            widget.setToolTip(tip)
        self._form.addRow(text_label, widget)
        if key:
            self.rows[key] = widget
        return widget

    def add_full(self, widget, key=None):
        self._form.addRow(widget)
        if key:
            self.rows[key] = widget
        return widget

    def add_section(self, text, trailing=None):
        """Título de sección, con un control opcional a la derecha."""
        row = QWidget()
        box = QHBoxLayout(row)
        box.setContentsMargins(0, 10, 0, 2)
        box.addWidget(label(text.upper(), "sectionTitle"))
        box.addStretch()
        if trailing is not None:
            box.addWidget(trailing)
        self._form.addRow(row)
        return row

    def set_row_visible(self, key, visible):
        self._form.setRowVisible(self.rows[key], visible)


def panel(*children, spacing=0):
    """Tarjeta con borde y fondo propios."""
    frame = QFrame()
    frame.setObjectName("panel")
    box = QVBoxLayout(frame)
    box.setContentsMargins(16, 14, 16, 16)
    box.setSpacing(spacing)
    for child in children:
        if isinstance(child, QWidget):
            box.addWidget(child)
        else:
            box.addLayout(child)
    return frame


def button(text, name="ghost", tip=None, on_click=None):
    widget = QPushButton(text)
    widget.setObjectName(name)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if tip:
        widget.setToolTip(tip)
    if on_click:
        widget.clicked.connect(on_click)
    return widget


def ask_text(parent, title, prompt, text=""):
    """Pide un texto con los botones en español. Devuelve None si se cancela."""
    dialog = QInputDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setLabelText(prompt)
    dialog.setTextValue(text)
    dialog.setOkButtonText("Guardar")
    dialog.setCancelButtonText("Cancelar")
    return dialog.textValue() if dialog.exec() else None


def confirm(parent, title, text, accept_label):
    box = QMessageBox(QMessageBox.Icon.Question, title, text, QMessageBox.StandardButton.NoButton, parent)
    accept = box.addButton(accept_label, QMessageBox.ButtonRole.AcceptRole)
    box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
    box.exec()
    return box.clickedButton() is accept


def notify(parent, title, text, icon=QMessageBox.Icon.Warning):
    box = QMessageBox(icon, title, text, QMessageBox.StandardButton.NoButton, parent)
    box.addButton("Aceptar", QMessageBox.ButtonRole.AcceptRole)
    box.exec()


def launch_command(literal=False):
    """Orden con la que se ejecuta el programa. Si está instalado se usa el
    comando corto y, si no, la ruta a run.py.

    Con literal=True todo va en rutas absolutas, sin $HOME y con el intérprete
    completo: es lo que necesita un archivo .desktop, que no expande variables
    de entorno ni busca en el PATH de la sesión. Sin literal, la línea es la
    que se pega en hyprland.conf, donde $HOME sí se expande y se lee mejor.
    """
    installed = shutil.which(DESKTOP_NAME)
    if installed:
        return installed if literal else DESKTOP_NAME
    path = str(project_root() / "run.py")
    if literal:
        return f'{sys.executable} "{path}"'
    home = str(Path.home())
    if path.startswith(home + os.sep):
        path = "$HOME" + path[len(home):]
    return f'python "{path}"'


def segmented(options, on_change):
    """Grupo pequeño de botones excluyentes, como el de las pestañas."""
    widget = QWidget()
    row = QHBoxLayout(widget)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(2)
    group = QButtonGroup(widget)
    buttons = {}
    for value, text in options:
        item = button(text, "tab")
        item.setCheckable(True)
        item.clicked.connect(lambda _checked=False, v=value: on_change(v))
        group.addButton(item)
        row.addWidget(item)
        buttons[value] = item
    return widget, buttons


# ---------------------------------------------------------------------------
# Ventana
# ---------------------------------------------------------------------------
class SettingsWindow(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.cfg = load_config()
        self.profiles = load_profiles()
        self.sliders = {}
        self.value_labels = {}
        self.suffixes = {}

        self.setObjectName("root")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(STYLESHEET)
        self.setWindowTitle("Crosshair")
        self.setWindowIcon(app_icon())
        # Al abrirse, el foco se queda en la ventana: así ningún control
        # aparece resaltado sin que el usuario lo haya tocado
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        root = QVBoxLayout(self)
        # Sin esto, al mostrarse la ventana el diseño vuelve a calcular el
        # tamaño mínimo y deshace el setFixedSize de más abajo
        root.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        root.setContentsMargins(METRICS["pad"], 16, METRICS["pad"], METRICS["pad"])
        root.setSpacing(14)
        root.addLayout(self._build_header())

        columns = QHBoxLayout()
        columns.setSpacing(16)
        columns.addLayout(self._build_rail())
        columns.addLayout(self._build_tabs())
        root.addLayout(columns)

        self._fix_size(root)
        self._refresh_profiles()
        self._sync()
        controller.state_changed.connect(self.set_overlay_state)
        self.set_overlay_state(controller.is_running())

    # --- cabecera -----------------------------------------------------------
    def _build_header(self):
        logo = QLabel()
        logo.setPixmap(app_icon().pixmap(34, 34))

        titles = QVBoxLayout()
        titles.setSpacing(1)
        titles.addWidget(label("Crosshair", "title"))
        titles.addWidget(label(f"v{__version__} · {__author__}", "subtitle"))

        self.status_pill = label("", "statusPill")

        header = QHBoxLayout()
        header.setSpacing(12)
        header.addWidget(logo)
        header.addLayout(titles)
        header.addStretch()
        header.addWidget(self.status_pill)
        return header

    # --- columna izquierda --------------------------------------------------
    def _build_rail(self):
        self.preview = Preview(self.cfg)
        self.preview.background_changed.connect(lambda _name: self._refresh_hint())

        self.hint = label("", "hint")
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.profile_combo = Combo()
        self.profile_combo.setToolTip("Perfiles guardados")
        self.profile_combo.activated.connect(self._on_profile_chosen)

        self.save_btn = button("Guardar", tip="Guardar la mira actual como perfil", on_click=self._save_profile)
        self.delete_btn = button("Eliminar", on_click=self._delete_profile)
        self.more_btn = button("···", tip="Importar y exportar")
        self.more_btn.setFixedWidth(38)
        menu = QMenu(self.more_btn)
        menu.addAction("Importar mira…", self._import_profile)
        menu.addAction("Exportar mira…", self._export_profile)
        self.more_btn.setMenu(menu)

        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        buttons.addWidget(self.save_btn, 1)
        buttons.addWidget(self.delete_btn, 1)
        buttons.addWidget(self.more_btn)

        profiles_panel = panel(label("PERFIL", "sectionTitle"), self.profile_combo, buttons, spacing=10)

        self.overlay_btn = button("", "primary", on_click=self._on_overlay_clicked)
        self.overlay_btn.setCheckable(True)

        rail = QVBoxLayout()
        rail.setSpacing(10)
        rail.addWidget(self.preview)
        rail.addWidget(self.hint)
        rail.addWidget(profiles_panel)
        rail.addStretch()
        rail.addWidget(self.overlay_btn)
        return rail

    # --- pestañas -----------------------------------------------------------
    def _build_tabs(self):
        self.stack = QStackedLayout()
        pages = [("Mira", self._page_crosshair()), ("Posición", self._page_position()),
                 ("Ajustes", self._page_settings())]

        tab_row = QHBoxLayout()
        tab_row.setSpacing(4)
        group = QButtonGroup(self)
        for index, (name, page) in enumerate(pages):
            tab = button(name, "tab")
            tab.setCheckable(True)
            tab.setChecked(index == 0)
            tab.clicked.connect(lambda _checked=False, i=index: self.stack.setCurrentIndex(i))
            group.addButton(tab)
            tab_row.addWidget(tab)
            self.stack.addWidget(panel(page))
        tab_row.addStretch()

        column = QVBoxLayout()
        column.setSpacing(10)
        column.addLayout(tab_row)
        column.addLayout(self.stack)
        return column

    def _page_crosshair(self):
        form = self.shape_form = Form()
        form.setFixedWidth(METRICS["panel_w"] - 32)

        head = QWidget()
        head_row = QHBoxLayout(head)
        head_row.setContentsMargins(0, 0, 0, 2)
        head_row.addWidget(label("ESTILO", "sectionTitle"))
        head_row.addStretch()
        self.style_name = label("", "styleName")
        head_row.addWidget(self.style_name)
        form.add_full(head)

        self.style_selector = StyleSelector(STYLES)
        self.style_selector.selected.connect(self._on_style_chosen)
        form.add_full(self.style_selector)
        form.add_full(rule())

        self.image_btn = button("", "colorBtn", tip="PNG o SVG · clic para elegir otra imagen",
                                on_click=self._choose_image)
        form.add("Imagen", self.image_btn, "image")
        self._slider(form, "Tamaño", "image_size")
        self._slider(form, "Opacidad", "image_opacity", " %")

        self.color_btn = ColorButton(self.cfg["color"], "Color de la mira")
        self.color_btn.color_changed.connect(lambda rgba: self._set("color", rgba))
        form.add("Color", self.color_btn, "color")

        self._slider(form, "Grosor", "thickness")
        self._slider(form, "Largo de los brazos", "arm")
        self._slider(form, "Separación central", "gap")
        self._slider(form, "Radio del círculo", "circle_radius")

        self.dot_switch = Switch()
        self.dot_switch.toggled.connect(lambda on: self._set("center_dot", on))
        form.add("Punto central", self.dot_switch, "center_dot")
        self._slider(form, "Radio del punto", "dot_radius")

        self.outline_switch = Switch()
        self.outline_switch.toggled.connect(lambda on: self._set("outline", on))
        self.outline_section = form.add_section("Contorno", self.outline_switch)

        self.outline_color_btn = ColorButton(self.cfg["outline_color"], "Color del contorno")
        self.outline_color_btn.color_changed.connect(lambda rgba: self._set("outline_color", rgba))
        form.add("Color", self.outline_color_btn, "outline_color")
        self._slider(form, "Grosor", "outline_thickness")
        return form

    def _page_position(self):
        form = Form()
        form.setFixedWidth(METRICS["panel_w"] - 32)

        form.add_section("Monitor")
        self.monitor_combo = Combo()
        self.monitor_combo.setToolTip("Monitor donde se muestra la mira")
        self.monitor_combo.activated.connect(self._on_monitor_chosen)
        form.add_full(self.monitor_combo)

        self.center_btn = button("Centrar", "quiet", tip="Devolver la mira al centro de la pantalla",
                                 on_click=self._center)
        form.add_section("Desplazamiento", self.center_btn)

        self.pad = PositionPad()
        self.pad.moved.connect(self._on_pad_moved)
        pad_box = QWidget()
        pad_layout = QVBoxLayout(pad_box)
        pad_layout.setContentsMargins(0, 2, 0, 6)
        pad_layout.setSpacing(6)
        pad_layout.addWidget(self.pad, 0, Qt.AlignmentFlag.AlignHCenter)
        pad_hint = label("Arrastra dentro del recuadro para colocar la mira", "hint")
        pad_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pad_layout.addWidget(pad_hint)
        form.add_full(pad_box)

        self.offset_sliders = {}
        self.offset_boxes = {}
        self._offset_row(form, "Horizontal", "offset_x", "Positivo: hacia la derecha")
        self._offset_row(form, "Vertical", "offset_y", "Positivo: hacia arriba")
        return form

    def _page_settings(self):
        form = Form()
        form.setFixedWidth(METRICS["panel_w"] - 32)

        form.add_section("Inicio")
        self.autostart_switch = Switch()
        self.autostart_switch.setChecked(autostart.is_enabled())
        self.autostart_switch.toggled.connect(self._on_autostart)
        form.add("Iniciar con la sesión", self.autostart_switch,
                 tip="Crea un acceso en ~/.config/autostart")
        self.autostart_hint = label("", "hint")
        self.autostart_hint.setWordWrap(True)
        form.add_full(self.autostart_hint)
        self._refresh_autostart_hint()

        # Hyprland 0.55 pasó su configuración de hyprland.conf a hyprland.lua.
        # Se mira cuál tiene el usuario y se le enseña la que le sirve.
        self.hypr_detected = hyprland.detect_flavour()
        self.hypr_flavour = self.hypr_detected or hyprland.LUA
        picker, self.hypr_buttons = segmented(
            [(hyprland.LUA, "hyprland.lua"), (hyprland.CONF, "hyprland.conf")], self._on_flavour
        )
        self.hypr_buttons[self.hypr_flavour].setChecked(True)
        form.add_section("Atajos de teclado", picker)

        self.hypr_hint = label("", "hint")
        self.hypr_hint.setWordWrap(True)
        self.hypr_hint.setFixedHeight(3 * self.hypr_hint.fontMetrics().height())
        self.hypr_hint.setAlignment(Qt.AlignmentFlag.AlignTop)
        form.add_full(self.hypr_hint)

        self.code_box = QPlainTextEdit()
        self.code_box.setObjectName("codeBox")
        self.code_box.setReadOnly(True)
        self.code_box.setFixedHeight(164)
        self.code_box.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.code_box.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        form.add_full(self.code_box)
        self.copy_btn = button("Copiar las líneas", "quiet", on_click=self._copy_bind)
        form.add_full(self.copy_btn)
        self._refresh_hyprland()

        form.add_section("Mantenimiento")
        row = QWidget()
        row_box = QHBoxLayout(row)
        row_box.setContentsMargins(0, 0, 0, 0)
        row_box.setSpacing(6)
        row_box.addWidget(button("Abrir carpeta de configuración", "quiet", on_click=self._open_config_dir))
        row_box.addWidget(button("Restablecer la mira", "quiet",
                                 tip="Vuelve a la mira predeterminada; la posición no cambia",
                                 on_click=self._reset))
        row_box.addStretch()
        form.add_full(row)

        about = label(f"Crosshair {__version__} · {__author__}\n{CONFIG_DIR}", "hint")
        about.setWordWrap(True)
        form.add_full(about)
        return form

    # --- filas con deslizador ----------------------------------------------
    def _slider(self, form, text, key, suffix=""):
        low, high = LIMITS[key]
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(low, high)
        slider.setCursor(Qt.CursorShape.PointingHandCursor)
        slider.valueChanged.connect(lambda value, k=key: self._on_slider(k, value))

        value_label = label("", "value")
        value_label.setFixedWidth(38)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        row.addWidget(slider)
        row.addWidget(value_label)

        form.add(text, container, key)
        self.sliders[key] = slider
        self.value_labels[key] = value_label
        self.suffixes[key] = suffix

    def _offset_row(self, form, text, key, tip):
        """Deslizador para mover rápido y casilla para ajustar de píxel en píxel."""
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setObjectName("centered")
        slider.setRange(-OFFSET_LIMIT, OFFSET_LIMIT)
        slider.setPageStep(10)
        slider.setCursor(Qt.CursorShape.PointingHandCursor)

        box = QSpinBox()
        box.setObjectName("numberBox")
        box.setRange(-OFFSET_LIMIT, OFFSET_LIMIT)
        box.setSuffix(" px")
        box.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        box.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        box.setKeyboardTracking(False)  # lo escrito se aplica con Enter o al salir
        box.setFixedWidth(box.fontMetrics().horizontalAdvance(f"-{OFFSET_LIMIT} px") + 26)

        slider.valueChanged.connect(lambda value, k=key: self._on_offset(k, value))
        box.valueChanged.connect(lambda value, k=key: self._on_offset(k, value))

        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        row.addWidget(slider)
        row.addWidget(box)
        form.add(text, container, key, tip)
        self.offset_sliders[key] = slider
        self.offset_boxes[key] = box

    # --- tamaño fijo --------------------------------------------------------
    def _fix_size(self, layout):
        """La ventana no cambia de tamaño al cambiar de estilo o de pestaña: se
        mide con cada estilo y se queda con el caso más alto."""
        saved = self.cfg
        best = QSize(0, 0)
        for style, _name in STYLES:
            self.cfg = dict(saved, style=style, center_dot=True, outline=True)
            self._update_visibility()
            self.ensurePolished()
            layout.activate()
            hint = layout.sizeHint()
            best = QSize(max(best.width(), hint.width()), max(best.height(), hint.height()))
        self.cfg = saved
        self._update_visibility()
        self.setFixedSize(best)

    # --- sincronización de los controles ------------------------------------
    def _sync(self):
        """Pone en los controles lo que dice self.cfg, sin disparar guardados."""
        for key, slider in self.sliders.items():
            slider.blockSignals(True)
            slider.setValue(int(self.cfg[key]))
            slider.blockSignals(False)
            self.value_labels[key].setText(f"{int(self.cfg[key])}{self.suffixes[key]}")

        self.style_selector.set_style(self.cfg["style"])
        self.style_name.setText(STYLE_NAMES.get(self.cfg["style"], ""))

        for switch, key in ((self.dot_switch, "center_dot"), (self.outline_switch, "outline")):
            switch.blockSignals(True)
            switch.setChecked(bool(self.cfg[key]))
            switch.blockSignals(False)

        self.color_btn.set_color(self.cfg["color"])
        self.outline_color_btn.set_color(self.cfg["outline_color"])

        self._refresh_offsets()
        self._refresh_monitors()
        self._refresh_image_button()
        self._update_visibility()
        self._refresh_preview()
        self._update_profile_selection()

    def _refresh_preview(self):
        self.preview.set_config(self.cfg)
        self._refresh_hint()

    def _refresh_hint(self):
        background = PREVIEW_BACKGROUNDS[self.preview.bg_index][0]
        self.hint.setText(f"×{self.preview.zoom:g} · fondo {background} · clic para cambiar")

    def _refresh_offsets(self):
        for key in ("offset_x", "offset_y"):
            for widget in (self.offset_sliders[key], self.offset_boxes[key]):
                widget.blockSignals(True)
                widget.setValue(int(self.cfg[key]))
                widget.blockSignals(False)
        self.center_btn.setEnabled(self.cfg["offset_x"] != 0 or self.cfg["offset_y"] != 0)
        self.pad.set_state((self.cfg["offset_x"], self.cfg["offset_y"]), self._screen_size())

    def _screen_size(self):
        """Tamaño del monitor elegido, para dibujar el mapa de posición a escala."""
        name = self.cfg["monitor"]
        screens = QApplication.screens()
        chosen = next((s for s in screens if s.name() == name), None) or QApplication.primaryScreen()
        if chosen is None:
            return None
        size = chosen.geometry()
        return size.width(), size.height()

    def _refresh_monitors(self):
        """Lista de monitores: Automático, los conectados y, si el elegido no
        está conectado, también ese, para no perder la elección."""
        tooltip = Qt.ItemDataRole.ToolTipRole
        combo = self.monitor_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Automático", "")
        combo.setItemData(0, "Lo decide el compositor: en Hyprland, el monitor activo", tooltip)
        names = []
        for screen in QApplication.screens():
            name = screen.name()
            if not name or name in names:
                continue
            names.append(name)
            geometry = screen.geometry()
            combo.addItem(name, name)
            combo.setItemData(combo.count() - 1, f"{geometry.width()} × {geometry.height()}", tooltip)
        current = self.cfg["monitor"]
        if current and current not in names:
            combo.addItem(f"{current} (desconectado)", current)
            combo.setItemData(combo.count() - 1,
                              "No está conectado: mientras tanto la mira usa el monitor automático", tooltip)
        combo.setCurrentIndex(max(0, combo.findData(current)))
        combo.blockSignals(False)

    def _refresh_image_button(self):
        path = image_path(self.cfg["image"])
        if path is None:
            self.image_btn.setIcon(QIcon())
            self.image_btn.setText("  Elegir imagen…")
            return
        thumb = QPixmap(str(path)).scaled(
            20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.image_btn.setIcon(QIcon(thumb))
        self.image_btn.setIconSize(QSize(20, 20))
        name = self.image_btn.fontMetrics().elidedText(path.stem, Qt.TextElideMode.ElideMiddle, 170)
        self.image_btn.setText(f"  {name}")

    def _update_visibility(self):
        """Solo se ven los controles que aplican al estilo elegido."""
        style = self.cfg["style"]
        is_image = style == "image"
        has_dot = style in ("cross", "tcross", "x", "circle")
        show = {
            "image": is_image,
            "image_size": is_image,
            "image_opacity": is_image,
            "color": not is_image,
            "thickness": style in ("cross", "tcross", "x", "circle"),
            "arm": style in ("cross", "tcross", "x"),
            "gap": style in ("cross", "tcross", "x"),
            "circle_radius": style == "circle",
            "center_dot": has_dot,
            "dot_radius": style == "dot" or (has_dot and bool(self.cfg["center_dot"])),
            "outline_color": not is_image,
            "outline_thickness": not is_image,
        }
        for key, visible in show.items():
            self.shape_form.set_row_visible(key, visible)
        # El contorno no se aplica a las imágenes
        self.outline_section.setEnabled(not is_image)
        self.outline_switch.setEnabled(not is_image)
        for key in ("outline_color", "outline_thickness"):
            self.shape_form.rows[key].setEnabled(not is_image and bool(self.cfg["outline"]))

    # --- guardado -----------------------------------------------------------
    def _apply(self):
        """Actualiza la vista previa y guarda. El overlay se entera por el archivo."""
        self._refresh_preview()
        self._update_profile_selection()
        try:
            save_config(self.cfg)
        except OSError as error:
            log.error("No se pudo guardar la configuración: %s", error)

    def _set(self, key, value):
        self.cfg[key] = value
        self._update_visibility()
        self._apply()

    def _on_slider(self, key, value):
        self.value_labels[key].setText(f"{value}{self.suffixes[key]}")
        self._set(key, value)

    def _on_offset(self, key, value):
        self.cfg[key] = value
        self._refresh_offsets()
        self._apply()

    def _on_pad_moved(self, x, y):
        self.cfg["offset_x"], self.cfg["offset_y"] = x, y
        self._refresh_offsets()
        self._apply()

    def _center(self):
        self.cfg["offset_x"] = self.cfg["offset_y"] = 0
        self._refresh_offsets()
        self._apply()

    def _on_monitor_chosen(self, index):
        self.cfg["monitor"] = self.monitor_combo.itemData(index) or ""
        self._refresh_offsets()
        self._apply()
        # Quita la opción «(desconectado)» si ya no está elegida; se hace
        # después, cuando el desplegable termina de procesar la elección.
        QTimer.singleShot(0, self._refresh_monitors)

    def _on_style_chosen(self, style):
        # Al elegir «Imagen» sin imagen todavía se pide una; si se cancela, nada cambia
        if style == "image" and image_path(self.cfg["image"]) is None:
            if not self._choose_image():
                self.style_selector.set_style(self.cfg["style"])
            return
        self._set("style", style)
        self.style_name.setText(STYLE_NAMES.get(style, ""))

    def _choose_image(self):
        """Pide un PNG o SVG, lo importa y lo usa como mira. True si se aplicó."""
        filename, _filter = QFileDialog.getOpenFileName(
            self, "Elegir imagen para la mira", str(Path.home()), IMAGE_FILTER
        )
        if not filename:
            return False
        try:
            name = import_image(filename)
        except ImportError_ as error:
            notify(self, "No se pudo importar la imagen", str(error))
            return False
        self.cfg["image"] = name
        self.cfg["style"] = "image"
        self._sync()
        self._apply()
        self._cleanup_images()  # la imagen anterior se borra si nada más la usa
        return True

    # --- perfiles -----------------------------------------------------------
    def _profile_look(self, name):
        return builtin_profile(name) if name in BUILTIN_PROFILES else self.profiles[name]

    def _refresh_profiles(self):
        combo = self.profile_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(CUSTOM_LABEL, None)
        for name in BUILTIN_PROFILES:
            combo.addItem(name, name)
        if self.profiles:
            combo.insertSeparator(combo.count())
            for name in sorted(self.profiles, key=str.lower):
                combo.addItem(name, name)
        combo.blockSignals(False)
        self._update_profile_selection()

    def _update_profile_selection(self):
        combo = self.profile_combo
        current = appearance(self.cfg)
        selected = 0
        for i in range(combo.count()):
            name = combo.itemData(i)
            if name and self._profile_look(name) == current:
                selected = i
                break
        combo.blockSignals(True)
        combo.setCurrentIndex(selected)
        combo.blockSignals(False)
        name = combo.itemData(selected)
        self.delete_btn.setEnabled(bool(name) and name not in BUILTIN_PROFILES)

    def _on_profile_chosen(self, index):
        name = self.profile_combo.itemData(index)
        if name is None:  # «Personalizado» no es un perfil real
            self._update_profile_selection()
            return
        self.apply_look(self._profile_look(name))

    def current_look(self):
        """Aspecto de la mira actual, sin la posición."""
        return appearance(self.cfg)

    def apply_look(self, look):
        """Cambia el aspecto de la mira y deja la posición como estaba."""
        self.cfg = {**copy.deepcopy(look), **placement(self.cfg)}
        self._sync()
        self._apply()

    def _save_profile(self):
        current = self.profile_combo.currentData()
        suggestion = current if current and current not in BUILTIN_PROFILES else ""
        name = ask_text(self, "Guardar perfil", "Nombre del perfil:", suggestion)
        if name is None:
            return
        name = " ".join(name.split())[:40]
        if not name:
            return
        if name == CUSTOM_LABEL or name in BUILTIN_PROFILES:
            notify(self, "Nombre reservado", "Ese nombre lo usa un perfil incluido. Elige otro.")
            return
        if name in self.profiles and not confirm(
            self, "Reemplazar perfil", f"Ya existe un perfil llamado «{name}». ¿Quieres reemplazarlo?", "Reemplazar"
        ):
            return
        self.profiles[name] = appearance(copy.deepcopy(self.cfg))
        self._store_profiles()
        self._refresh_profiles()
        self._cleanup_images()  # por si el perfil reemplazado usaba otra imagen

    def _delete_profile(self):
        name = self.profile_combo.currentData()
        if not name or name in BUILTIN_PROFILES:
            return
        if not confirm(self, "Eliminar perfil",
                       f"¿Eliminar el perfil «{name}»? La mira actual no cambia.", "Eliminar"):
            return
        self.profiles.pop(name, None)
        self._store_profiles()
        self._refresh_profiles()
        self._cleanup_images()

    def _import_profile(self):
        filename, _filter = QFileDialog.getOpenFileName(
            self, "Importar mira", str(Path.home()), share.FILE_FILTER
        )
        if not filename:
            return
        try:
            look, name = share.import_from(filename)
        except share.ShareError as error:
            notify(self, "No se pudo importar", str(error))
            return
        self.apply_look(look)
        self._cleanup_images()
        notify(self, "Mira importada",
               f"Se aplicó «{name}». Pulsa Guardar si quieres conservarla como perfil.",
               QMessageBox.Icon.Information)

    def _export_profile(self):
        current = self.profile_combo.currentData() or "mira"
        suggested = str(Path.home() / f"{share.safe_stem(current)}{share.FILE_SUFFIX}")
        filename, _filter = QFileDialog.getSaveFileName(
            self, "Exportar mira", suggested, share.FILE_FILTER
        )
        if not filename:
            return
        try:
            path = share.export_to(filename, self.cfg, current)
        except share.ShareError as error:
            notify(self, "No se pudo exportar", str(error))
            return
        notify(self, "Mira exportada", f"Guardada en:\n{path}", QMessageBox.Icon.Information)

    def _store_profiles(self):
        try:
            save_profiles(self.profiles)
        except OSError as error:
            log.error("No se pudieron guardar los perfiles: %s", error)
            notify(self, "No se pudo guardar", "No se pudo escribir el archivo de perfiles.")

    def _cleanup_images(self):
        try:
            remove_unused_images(self.cfg, self.profiles)
        except OSError as error:
            log.warning("No se pudieron limpiar las imágenes: %s", error)

    def _reset(self):
        """Vuelve a la mira predeterminada; la posición no cambia."""
        self.apply_look(appearance(copy.deepcopy(DEFAULTS)))
        self._cleanup_images()

    # --- pestaña de ajustes -------------------------------------------------
    def _on_autostart(self, enabled):
        # El archivo .desktop necesita rutas absolutas, no $HOME
        if not autostart.set_enabled(enabled, launch_command(literal=True), DESKTOP_NAME):
            notify(self, "No se pudo cambiar", "No se pudo escribir en ~/.config/autostart.")
            self.autostart_switch.blockSignals(True)
            self.autostart_switch.setChecked(autostart.is_enabled())
            self.autostart_switch.blockSignals(False)
        self._refresh_autostart_hint()

    def _refresh_autostart_hint(self):
        self.autostart_hint.setText(
            "Activado. Si además tienes la línea exec-once en hyprland.conf, quita una de las dos."
            if self.autostart_switch.isChecked() else
            "Crea un acceso en ~/.config/autostart para abrir Crosshair en la bandeja al entrar."
        )

    def _on_flavour(self, flavour):
        self.hypr_flavour = flavour
        self._refresh_hyprland()

    def _refresh_hyprland(self):
        self.bind_text = hyprland.lines(self.hypr_flavour, launch_command())
        self.code_box.setPlainText(self.bind_text)
        self.hypr_hint.setText(hyprland.explanation(self.hypr_flavour, self.hypr_detected))

    def _copy_bind(self):
        QApplication.clipboard().setText(self.bind_text)
        self.copy_btn.setText("Copiado")
        QTimer.singleShot(1500, lambda: self.copy_btn.setText("Copiar las líneas"))

    def _open_config_dir(self):
        ensure_config_dir()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(CONFIG_DIR)))

    # --- estado del overlay -------------------------------------------------
    def _on_overlay_clicked(self, checked):
        self.controller.start() if checked else self.controller.stop()

    def set_overlay_state(self, running):
        self.overlay_btn.setChecked(running)
        self.overlay_btn.setText("Mira activada" if running else "Mira desactivada")
        self.overlay_btn.setToolTip("Clic para desactivar" if running else "Clic para activar")
        color = COLORS["ok"] if running else COLORS["muted"]
        self.status_pill.setText(
            f'<span style="color:{color}">●</span>&nbsp;&nbsp;' + ("Activa" if running else "Inactiva")
        )

    # --- eventos de la ventana ---------------------------------------------
    def showEvent(self, event):
        super().showEvent(event)
        self.setFocus()
        # Los perfiles pueden haber cambiado desde otra ventana o a mano
        self.profiles = load_profiles()
        self._refresh_profiles()
        self._refresh_monitors()
        self.autostart_switch.blockSignals(True)
        self.autostart_switch.setChecked(autostart.is_enabled())
        self.autostart_switch.blockSignals(False)
        self._refresh_autostart_hint()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()  # el programa sigue en la bandeja
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        # Cerrar la ventana solo la oculta: el programa sigue en la bandeja
        event.ignore()
        self.hide()
