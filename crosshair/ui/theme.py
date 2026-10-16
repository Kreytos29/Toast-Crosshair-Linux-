"""Tema oscuro de la ventana de ajustes.

Todos los colores y medidas salen de COLORS y METRICS, así que cambiar el
aspecto del programa es cambiar estos dos diccionarios.
"""

COLORS = {
    "bg": "#0e0f13",          # fondo de la ventana
    "panel": "#15171c",       # paneles y tarjetas
    "field": "#1c1f26",       # campos y controles
    "hover": "#232730",       # control bajo el puntero
    "line": "#23262e",        # bordes y separadores
    "text": "#e8eaee",        # texto principal
    "text2": "#a2a9b6",       # texto secundario
    "muted": "#6b7280",       # texto apagado y controles desactivados
    "accent": "#ff4d57",      # color de marca
    "accent_hi": "#ff6f78",   # color de marca bajo el puntero
    "accent_dim": "#4a2228",  # fondo tenue del color de marca
    "ok": "#2ecc71",          # indicador de mira activa
    "track": "#2b303a",       # canal de los deslizadores
}

METRICS = {
    "radius": 8,       # controles
    "radius_lg": 12,   # paneles
    "gap": 12,
    "pad": 20,
    "rail": 336,       # ancho de la columna izquierda (y lado de la vista previa)
    "panel_w": 452,    # ancho de la columna derecha
    "row_h": 30,       # alto mínimo de cada fila de ajustes
    "label_w": 132,    # ancho de las etiquetas, para que todo quede alineado
}

STYLESHEET = """
#root { background: %(bg)s; }

/* --- texto --- */
#title      { color: %(text)s;  font-size: 17px; font-weight: 600; }
#subtitle   { color: %(muted)s; font-size: 11px; }
#sectionTitle { color: %(text2)s; font-size: 11px; font-weight: 600; letter-spacing: 1px; }
#rowLabel   { color: %(text2)s; font-size: 12px; }
#value      { color: %(text)s;  font-size: 12px; }
#hint       { color: %(muted)s; font-size: 11px; }
#styleName  { color: %(text)s;  font-size: 12px; }

/* --- panel y separadores --- */
#panel { background: %(panel)s; border: 1px solid %(line)s; border-radius: %(radius_lg)spx; }
#rule  { background: %(line)s; border: none; max-height: 1px; min-height: 1px; }

/* --- indicador de estado --- */
#statusPill {
    color: %(text2)s; font-size: 11px; font-weight: 600; padding: 5px 12px;
    background: %(panel)s; border: 1px solid %(line)s; border-radius: 11px;
}

/* --- pestañas --- */
#tab {
    color: %(text2)s; font-size: 12px; font-weight: 500; padding: 7px 16px;
    background: transparent; border: none; border-radius: %(radius)spx;
}
#tab { color: %(muted)s; }
#tab:hover:!checked { color: %(text2)s; background: %(panel)s; }
#tab:checked { color: %(text)s; background: %(field)s; }

/* --- deslizadores --- */
QSlider::groove:horizontal { height: 4px; background: %(track)s; border-radius: 2px; }
QSlider::sub-page:horizontal { background: %(accent)s; border-radius: 2px; }
QSlider::handle:horizontal {
    background: %(text)s; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px;
}
QSlider::handle:horizontal:hover { background: %(accent_hi)s; }
QSlider::sub-page:horizontal:disabled { background: %(track)s; }
QSlider::handle:horizontal:disabled { background: %(muted)s; }
/* Los desplazamientos van de negativo a positivo: sin relleno a la izquierda */
QSlider#centered::sub-page:horizontal { background: %(track)s; }

/* --- campos --- */
QSpinBox#numberBox {
    padding: 4px 8px; color: %(text)s; font-size: 12px;
    background: %(field)s; border: 1px solid transparent; border-radius: 6px;
    selection-background-color: %(accent)s; selection-color: #ffffff;
}
QSpinBox#numberBox:hover { border-color: %(line)s; }
QSpinBox#numberBox:focus { border-color: %(accent)s; }

QComboBox#combo {
    padding: 7px 12px; color: %(text)s; font-size: 12px;
    background: %(field)s; border: 1px solid transparent; border-radius: %(radius)spx;
}
QComboBox#combo:hover { border-color: %(line)s; }
QComboBox#combo:focus { border-color: %(accent)s; }
QComboBox#combo::drop-down { border: none; width: 26px; }
QComboBox#combo::down-arrow { image: none; }
QComboBox#combo QAbstractItemView {
    background: %(field)s; color: %(text)s; border: 1px solid %(line)s;
    border-radius: %(radius)spx; padding: 4px; outline: 0;
    selection-background-color: %(accent)s; selection-color: #ffffff;
}

QPushButton#colorBtn {
    text-align: left; padding: 6px 10px; color: %(text)s; font-size: 12px;
    background: %(field)s; border: 1px solid transparent; border-radius: 6px;
}
QPushButton#colorBtn:hover { border-color: %(line)s; }
QPushButton#colorBtn:disabled { color: %(muted)s; }

QPlainTextEdit#codeBox {
    padding: 8px 10px; color: %(text2)s; font-family: monospace; font-size: 11px;
    background: %(bg)s; border: 1px solid %(line)s; border-radius: %(radius)spx;
    selection-background-color: %(accent)s; selection-color: #ffffff;
}

/* Barra de desplazamiento discreta, sin flechas */
QScrollBar:vertical {
    width: 8px; margin: 4px 2px; background: transparent; border: none;
}
QScrollBar::handle:vertical {
    background: %(track)s; border-radius: 3px; min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: %(muted)s; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; border: none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

/* --- botones --- */
QPushButton#primary {
    padding: 13px; font-size: 13px; font-weight: 600; color: #ffffff;
    background: %(accent)s; border: 1px solid %(accent)s; border-radius: 10px;
}
QPushButton#primary:hover { background: %(accent_hi)s; border-color: %(accent_hi)s; }
QPushButton#primary:!checked {
    color: %(text2)s; background: %(field)s; border-color: %(line)s;
}
QPushButton#primary:!checked:hover { color: %(text)s; background: %(hover)s; }

QPushButton#ghost {
    padding: 8px 12px; color: %(text2)s; font-size: 12px;
    background: %(field)s; border: 1px solid transparent; border-radius: %(radius)spx;
}
QPushButton#ghost:hover { color: %(text)s; background: %(hover)s; }
QPushButton#ghost:disabled { color: %(muted)s; background: transparent; border-color: %(line)s; }

QPushButton#quiet {
    padding: 5px 12px; color: %(text2)s; font-size: 11px;
    background: transparent; border: 1px solid %(line)s; border-radius: 6px;
}
QPushButton#quiet:hover { color: %(text)s; border-color: %(muted)s; }
QPushButton#quiet:disabled { color: %(muted)s; border-color: %(line)s; }

QPushButton#styleBtn {
    background: %(field)s; border: 1px solid transparent; border-radius: %(radius)spx;
}
QPushButton#styleBtn:hover:!checked { background: %(hover)s; }
QPushButton#styleBtn:checked { background: %(accent_dim)s; border-color: %(accent)s; }

/* La flecha que Qt añade a los botones con menú se dibuja a mano */
QPushButton::menu-indicator { image: none; width: 0; height: 0; }

/* --- menús --- */
QMenu {
    background: %(field)s; color: %(text)s; font-size: 12px;
    border: 1px solid %(line)s; border-radius: %(radius)spx; padding: 4px;
}
QMenu::item { padding: 6px 18px 6px 12px; border-radius: 5px; }
QMenu::item:selected { background: %(accent)s; color: #ffffff; }
QMenu::separator { height: 1px; background: %(line)s; margin: 4px 8px; }

/* --- diálogos del sistema con el mismo tema --- */
QMessageBox, QInputDialog, QFileDialog, QColorDialog { background: %(panel)s; }
QMessageBox QLabel, QInputDialog QLabel { color: %(text)s; font-size: 12px; }
QToolTip {
    color: %(text)s; background: %(field)s; border: 1px solid %(line)s;
    border-radius: 6px; padding: 5px 8px;
}
""" % {**COLORS, **METRICS}
