"""Ventana de ajustes. Se ejecuta sin pantalla con QT_QPA_PLATFORM=offscreen,
que sandbox.py ya deja puesto."""
import json
import unittest

import sandbox  # noqa: F401  (debe importarse primero)

from crosshair import autostart, config, share
from crosshair.paths import AUTOSTART_FILE, CONFIG_FILE, IMAGES_DIR

try:
    from PyQt6.QtCore import QObject, QPointF, Qt, pyqtSignal
    from PyQt6.QtGui import QMouseEvent
    from PyQt6.QtWidgets import QApplication
    HAVE_QT = True
except ImportError:  # pragma: no cover
    HAVE_QT = False

qapp = None


def setUpModule():
    if not HAVE_QT:
        raise unittest.SkipTest("hace falta PyQt6")
    global qapp
    qapp = QApplication.instance() or QApplication([])
    qapp.setStyle("Fusion")


if HAVE_QT:
    class FakeController(QObject):
        """Finge el proceso del overlay: aquí no se lanza nada de verdad."""

        state_changed = pyqtSignal(bool)

        def __init__(self):
            super().__init__()
            self.running = False

        def is_running(self):
            return self.running

        def is_active(self):
            return self.running

        def start(self):
            self.running = True
            self.state_changed.emit(True)

        def stop(self):
            self.running = False
            self.state_changed.emit(False)


class UITest(unittest.TestCase):
    def setUp(self):
        sandbox.reset()
        AUTOSTART_FILE.unlink(missing_ok=True)
        from crosshair.ui.window import SettingsWindow

        self.controller = FakeController()
        self.win = SettingsWindow(self.controller)
        self.win.show()
        QApplication.processEvents()

    def tearDown(self):
        self.win.close()
        self.win.deleteLater()
        QApplication.processEvents()

    def saved(self):
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))["crosshair"]


class TestVentana(UITest):
    def test_la_ventana_tiene_tamano_fijo(self):
        self.assertEqual(self.win.minimumSize(), self.win.maximumSize())

    def test_cambiar_de_estilo_no_cambia_el_tamano(self):
        size = self.win.size()
        for style, _name in self.win.style_selector.buttons.items():
            if style == "image":
                continue  # pediría un archivo
            self.win.style_selector.buttons[style].click()
            QApplication.processEvents()
            with self.subTest(style=style):
                self.assertEqual(self.win.size(), size)

    def test_las_pestanas_cambian_de_pagina(self):
        for index in (1, 2, 0):
            self.win.stack.setCurrentIndex(index)
            QApplication.processEvents()
            self.assertEqual(self.win.stack.currentIndex(), index)

    def test_el_boton_grande_refleja_el_estado(self):
        self.controller.start()
        QApplication.processEvents()
        self.assertTrue(self.win.overlay_btn.isChecked())
        self.assertIn("activada", self.win.overlay_btn.text())
        self.controller.stop()
        QApplication.processEvents()
        self.assertFalse(self.win.overlay_btn.isChecked())


class TestControlesDeLaMira(UITest):
    def test_mover_un_deslizador_guarda(self):
        self.win.sliders["arm"].setValue(23)
        self.assertEqual(self.saved()["arm"], 23)
        self.assertIn("23", self.win.value_labels["arm"].text())

    def test_cada_estilo_muestra_solo_sus_controles(self):
        casos = {
            "cross": {"arm": True, "circle_radius": False, "center_dot": True},
            "tcross": {"arm": True, "circle_radius": False, "center_dot": True},
            "x": {"arm": True, "circle_radius": False, "center_dot": True},
            "dot": {"arm": False, "circle_radius": False, "center_dot": False},
            "circle": {"arm": False, "circle_radius": True, "center_dot": True},
        }
        for style, expected in casos.items():
            self.win.style_selector.buttons[style].click()
            QApplication.processEvents()
            for key, visible in expected.items():
                with self.subTest(style=style, key=key):
                    self.assertEqual(self.win.shape_form.rows[key].isVisible(), visible)

    def test_el_punto_central_apaga_su_radio(self):
        self.win.style_selector.buttons["cross"].click()
        self.win.dot_switch.setChecked(False)
        QApplication.processEvents()
        self.assertFalse(self.win.shape_form.rows["dot_radius"].isVisible())
        self.win.dot_switch.setChecked(True)
        QApplication.processEvents()
        self.assertTrue(self.win.shape_form.rows["dot_radius"].isVisible())

    def test_apagar_el_contorno_atenua_sus_controles(self):
        self.win.outline_switch.setChecked(False)
        QApplication.processEvents()
        self.assertFalse(self.win.shape_form.rows["outline_color"].isEnabled())
        self.assertFalse(self.saved()["outline"])

    def test_el_estilo_imagen_no_se_aplica_sin_imagen(self):
        """Al pulsarlo se abriría el selector de archivos; aquí se simula que se
        cancela y el estilo debe quedarse como estaba."""
        self.win._choose_image = lambda: False
        self.win._on_style_chosen("image")
        QApplication.processEvents()
        self.assertNotEqual(self.win.cfg["style"], "image")


class TestPosicion(UITest):
    def test_el_deslizador_y_la_casilla_van_juntos(self):
        self.win.offset_sliders["offset_x"].setValue(-137)
        self.assertEqual(self.win.offset_boxes["offset_x"].value(), -137)
        self.assertEqual(self.saved()["offset_x"], -137)

    def test_la_casilla_mueve_el_deslizador(self):
        self.win.offset_boxes["offset_y"].setValue(88)
        self.assertEqual(self.win.offset_sliders["offset_y"].value(), 88)
        self.assertEqual(self.saved()["offset_y"], 88)

    def test_no_se_puede_pasar_del_limite(self):
        self.win.offset_boxes["offset_x"].setValue(99999)
        self.assertLessEqual(abs(self.saved()["offset_x"]), config.OFFSET_LIMIT)

    def test_centrar(self):
        self.win.offset_sliders["offset_x"].setValue(50)
        self.assertTrue(self.win.center_btn.isEnabled())
        self.win.center_btn.click()
        self.assertEqual((self.saved()["offset_x"], self.saved()["offset_y"]), (0, 0))
        self.assertFalse(self.win.center_btn.isEnabled())

    def test_arrastrar_en_el_mapa_mueve_la_mira(self):
        pad = self.win.pad
        pad.set_state((0, 0), (1920, 1080))
        # Un clic a la izquierda y por encima del centro
        point = QPointF(pad.width() / 2 - 40, pad.height() / 2 - 20)
        pad.mousePressEvent(QMouseEvent(
            QMouseEvent.Type.MouseButtonPress, point, point,
            Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        QApplication.processEvents()
        self.assertLess(self.saved()["offset_x"], 0, "a la izquierda del centro es negativo")
        self.assertGreater(self.saved()["offset_y"], 0, "por encima del centro es positivo")

    def test_el_mapa_no_se_sale_del_limite(self):
        pad = self.win.pad
        pad.set_state((0, 0), (1920, 1080))
        point = QPointF(1.0, 1.0)  # esquina superior izquierda
        pad.mousePressEvent(QMouseEvent(
            QMouseEvent.Type.MouseButtonPress, point, point,
            Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        self.assertGreaterEqual(self.saved()["offset_x"], -config.OFFSET_LIMIT)
        self.assertLessEqual(self.saved()["offset_y"], config.OFFSET_LIMIT)

    def test_el_monitor_guardado_aunque_no_este_conectado(self):
        self.win.cfg["monitor"] = "DP-99"
        self.win._refresh_monitors()
        self.assertEqual(self.win.monitor_combo.currentData(), "DP-99")
        self.assertIn("desconectado", self.win.monitor_combo.currentText())

    def test_volver_a_automatico_quita_la_opcion_desconectada(self):
        self.win.cfg["monitor"] = "DP-99"
        self.win._refresh_monitors()
        self.win.monitor_combo.setCurrentIndex(0)
        self.win.monitor_combo.activated.emit(0)
        QApplication.processEvents()
        self.assertEqual(self.saved()["monitor"], "")
        textos = [self.win.monitor_combo.itemText(i) for i in range(self.win.monitor_combo.count())]
        self.assertFalse(any("desconectado" in t for t in textos))


class TestPerfiles(UITest):
    def choose(self, name):
        index = self.win.profile_combo.findData(name)
        self.assertGreaterEqual(index, 0, f"no está el perfil {name}")
        self.win.profile_combo.setCurrentIndex(index)
        self.win.profile_combo.activated.emit(index)
        QApplication.processEvents()

    def test_elegir_un_perfil_cambia_la_mira(self):
        self.choose("Punto verde")
        self.assertEqual(self.saved()["style"], "dot")

    def test_elegir_un_perfil_respeta_la_posicion(self):
        self.win.offset_sliders["offset_x"].setValue(77)
        self.win.cfg["monitor"] = "DP-1"
        self.choose("Aspa fina")
        self.assertEqual(self.saved()["style"], "x")
        self.assertEqual(self.saved()["offset_x"], 77)
        self.assertEqual(self.saved()["monitor"], "DP-1")

    def test_una_mira_cualquiera_sale_como_personalizado(self):
        self.win.sliders["arm"].setValue(31)
        self.assertEqual(self.win.profile_combo.currentText(), "Personalizado")

    def test_guardar_y_borrar_un_perfil(self):
        self.win.sliders["arm"].setValue(29)
        self.win._ask = None
        import crosshair.ui.window as window_module
        window_module.ask_text = lambda *a, **k: "El mío"
        self.win._save_profile()
        QApplication.processEvents()
        self.assertIn("El mío", config.load_profiles())
        self.assertEqual(self.win.profile_combo.currentText(), "El mío")
        self.assertTrue(self.win.delete_btn.isEnabled())

        window_module.confirm = lambda *a, **k: True
        self.win._delete_profile()
        QApplication.processEvents()
        self.assertNotIn("El mío", config.load_profiles())

    def test_no_se_puede_usar_el_nombre_de_un_perfil_incluido(self):
        import crosshair.ui.window as window_module
        window_module.ask_text = lambda *a, **k: "Punto verde"
        window_module.notify = lambda *a, **k: None
        self.win._save_profile()
        self.assertNotIn("Punto verde", config.load_profiles())

    def test_los_perfiles_guardados_no_llevan_la_posicion(self):
        import crosshair.ui.window as window_module
        window_module.ask_text = lambda *a, **k: "Con posición"
        self.win.offset_sliders["offset_y"].setValue(66)
        self.win._save_profile()
        self.assertNotIn("offset_y", config.load_profiles()["Con posición"])

    def test_restablecer_mantiene_la_posicion(self):
        self.win.offset_sliders["offset_x"].setValue(45)
        self.win.sliders["arm"].setValue(33)
        self.win._reset()
        self.assertEqual(self.saved()["arm"], config.DEFAULTS["arm"])
        self.assertEqual(self.saved()["offset_x"], 45)

    def test_importar_una_mira(self):
        path = sandbox.TMP / "importada.crosshair.json"
        share.export_to(path, config.sanitize_config({"style": "circle", "circle_radius": 30}), "Anillo")
        import crosshair.ui.window as window_module
        window_module.notify = lambda *a, **k: None
        window_module.QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(path), ""))
        self.win._import_profile()
        QApplication.processEvents()
        self.assertEqual(self.saved()["style"], "circle")
        self.assertEqual(self.saved()["circle_radius"], 30)

    def test_exportar_la_mira_actual(self):
        path = sandbox.TMP / "exportada.json"
        path.unlink(missing_ok=True)
        import crosshair.ui.window as window_module
        window_module.notify = lambda *a, **k: None
        window_module.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(path), ""))
        self.win.sliders["thickness"].setValue(6)
        self.win._export_profile()
        self.assertTrue(path.is_file())
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["crosshair"]["thickness"], 6)


class TestAjustes(UITest):
    def test_el_interruptor_crea_y_borra_el_acceso_de_inicio(self):
        self.assertFalse(autostart.is_enabled())
        self.win.autostart_switch.setChecked(True)
        QApplication.processEvents()
        self.assertTrue(AUTOSTART_FILE.is_file())
        self.assertIn("--hidden", AUTOSTART_FILE.read_text(encoding="utf-8"))
        self.win.autostart_switch.setChecked(False)
        QApplication.processEvents()
        self.assertFalse(AUTOSTART_FILE.exists())

    def test_el_acceso_de_inicio_no_usa_variables_de_entorno(self):
        """Un archivo .desktop no expande $HOME ni busca en el PATH, así que la
        línea Exec tiene que llevar rutas absolutas."""
        self.win.autostart_switch.setChecked(True)
        QApplication.processEvents()
        exec_line = next(line for line in AUTOSTART_FILE.read_text(encoding="utf-8").splitlines()
                         if line.startswith("Exec="))
        self.assertNotIn("$", exec_line)
        self.assertIn("/", exec_line.split("=", 1)[1].split()[0])

    def test_la_linea_de_hyprland_abrevia_la_carpeta_personal(self):
        """En hyprland.conf sí se expande $HOME, y así la línea se lee mejor.
        Se finge que el proyecto está dentro de la carpeta personal."""
        import shutil

        import crosshair.ui.window as window_module

        if shutil.which("crosshair"):
            self.skipTest("con el programa instalado se usa el comando corto, sin rutas")
        real_home = window_module.Path.home
        root = window_module.project_root().parent
        window_module.Path.home = staticmethod(lambda: root)
        try:
            self.assertIn("$HOME", window_module.launch_command())
            self.assertNotIn("$HOME", window_module.launch_command(literal=True))
        finally:
            window_module.Path.home = real_home

    def test_las_lineas_del_atajo_tienen_lo_necesario(self):
        from crosshair import hyprland

        for flavour, fragments in (
            (hyprland.LUA, ("hl.on", "hl.bind", "hl.window_rule")),
            (hyprland.CONF, ("exec-once", "bind =", "windowrule")),
        ):
            self.win.hypr_buttons[flavour].click()
            QApplication.processEvents()
            with self.subTest(flavour=flavour):
                for fragment in fragments + ("--hidden", "--toggle", "--next-profile"):
                    self.assertIn(fragment, self.win.bind_text)

    def test_el_selector_empieza_en_el_formato_detectado(self):
        """Sin configuración de Hyprland se ofrece Lua, que es el formato nuevo."""
        from crosshair import hyprland

        esperado = self.win.hypr_detected or hyprland.LUA
        self.assertTrue(self.win.hypr_buttons[esperado].isChecked())

    def test_cambiar_de_formato_cambia_el_texto(self):
        from crosshair import hyprland

        self.win.hypr_buttons[hyprland.CONF].click()
        QApplication.processEvents()
        conf = self.win.bind_text
        self.win.hypr_buttons[hyprland.LUA].click()
        QApplication.processEvents()
        self.assertNotEqual(conf, self.win.bind_text)
        self.assertEqual(self.win.code_box.toPlainText(), self.win.bind_text)

    def test_copiar_las_lineas(self):
        from PyQt6.QtWidgets import QApplication as QA
        self.win.copy_btn.click()
        self.assertEqual(QA.clipboard().text(), self.win.bind_text)


class TestImagenes(UITest):
    def test_importar_un_png_y_usarlo(self):
        from crosshair.ui.images import import_image

        source = sandbox.TMP / "origen.png"
        source.write_bytes(sandbox.png_bytes(16))
        name = import_image(source)
        self.assertTrue((IMAGES_DIR / name).is_file())

        self.win.cfg["image"] = name
        self.win.cfg["style"] = "image"
        self.win._sync()
        self.win._apply()
        QApplication.processEvents()
        self.assertEqual(self.saved()["style"], "image")
        self.assertTrue(self.win.shape_form.rows["image_size"].isVisible())
        self.assertFalse(self.win.shape_form.rows["arm"].isVisible())
        self.assertFalse(self.win.outline_switch.isEnabled(), "el contorno no aplica a las imágenes")

    def test_una_imagen_rota_da_un_error_claro(self):
        from crosshair.ui.images import ImportError_, import_image

        bad = sandbox.TMP / "rota.png"
        bad.write_bytes(b"esto no es un png")
        with self.assertRaises(ImportError_):
            import_image(bad)


if __name__ == "__main__":
    unittest.main()
