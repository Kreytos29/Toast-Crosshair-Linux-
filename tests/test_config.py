"""Validación de la configuración, perfiles y migración desde la versión anterior."""
import json
import unittest

import sandbox  # noqa: F401  (debe importarse primero)

from crosshair import config
from crosshair.paths import CONFIG_FILE, IMAGES_DIR, LEGACY_PROFILES_FILE, PROFILES_FILE


class TestSanitize(unittest.TestCase):
    def setUp(self):
        sandbox.reset()

    def test_un_archivo_vacio_da_los_valores_por_defecto(self):
        self.assertEqual(config.sanitize_config(None), config.DEFAULTS)
        self.assertEqual(config.sanitize_config("no soy un diccionario"), config.DEFAULTS)

    def test_se_ignoran_las_claves_desconocidas(self):
        self.assertNotIn("loquesea", config.sanitize_config({"loquesea": 1}))

    def test_los_numeros_se_limitan_a_su_rango(self):
        for key, (low, high) in config.LIMITS.items():
            with self.subTest(key=key):
                self.assertEqual(config.sanitize_config({key: high + 1000})[key], high)
                self.assertEqual(config.sanitize_config({key: low - 1000})[key], low)

    def test_los_valores_imposibles_vuelven_al_predeterminado(self):
        for value in (float("nan"), float("inf"), "8", None, True, [1]):
            with self.subTest(value=repr(value)):
                self.assertEqual(config.sanitize_config({"thickness": value})["thickness"],
                                 config.DEFAULTS["thickness"])

    def test_los_decimales_se_redondean(self):
        self.assertEqual(config.sanitize_config({"offset_x": -7.6})["offset_x"], -8)

    def test_un_estilo_inventado_vuelve_a_la_cruz(self):
        self.assertEqual(config.sanitize_config({"style": "banana"})["style"], "cross")

    def test_los_estilos_nuevos_se_aceptan(self):
        for style in ("tcross", "x", "dot", "circle"):
            with self.subTest(style=style):
                self.assertEqual(config.sanitize_config({"style": style})["style"], style)

    def test_los_colores_mal_formados_vuelven_al_predeterminado(self):
        for value in ([1, 2], "rojo", [1, 1, 1, "a"], None):
            with self.subTest(value=repr(value)):
                self.assertEqual(config.sanitize_config({"color": value})["color"],
                                 config.DEFAULTS["color"])

    def test_los_colores_se_recortan_entre_cero_y_uno(self):
        self.assertEqual(config.sanitize_config({"color": [5, -2, 0.5, 1]})["color"],
                         [1.0, 0.0, 0.5, 1.0])

    def test_la_imagen_no_puede_ser_una_ruta(self):
        cfg = config.sanitize_config({"image": "../../../etc/passwd"})
        self.assertEqual(cfg["image"], "passwd")

    def test_sin_imagen_el_estilo_imagen_vuelve_a_la_cruz(self):
        self.assertEqual(config.sanitize_config({"style": "image", "image": "no-existe.png"})["style"],
                         "cross")

    def test_con_imagen_el_estilo_imagen_se_mantiene(self):
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        (IMAGES_DIR / "mia.png").write_bytes(sandbox.png_bytes())
        self.assertEqual(config.sanitize_config({"style": "image", "image": "mia.png"})["style"],
                         "image")

    def test_el_nombre_del_monitor_se_limpia(self):
        self.assertEqual(config.sanitize_config({"monitor": "  DP-1  "})["monitor"], "DP-1")
        self.assertEqual(config.sanitize_config({"monitor": 5})["monitor"], "")
        self.assertEqual(len(config.sanitize_config({"monitor": "x" * 200})["monitor"]), 64)


class TestAspectoYPosicion(unittest.TestCase):
    def test_el_aspecto_no_lleva_las_claves_de_posicion(self):
        look = config.appearance(config.sanitize_config({}))
        for key in config.PLACEMENT_KEYS:
            self.assertNotIn(key, look)

    def test_aspecto_y_posicion_juntos_dan_la_configuracion_completa(self):
        cfg = config.sanitize_config({"offset_x": 5, "monitor": "DP-1"})
        self.assertEqual({**config.appearance(cfg), **config.placement(cfg)}, cfg)

    def test_los_perfiles_incluidos_no_guardan_la_posicion(self):
        for name in config.BUILTIN_PROFILES:
            with self.subTest(name=name):
                self.assertEqual(set(config.builtin_profile(name)),
                                 set(config.DEFAULTS) - set(config.PLACEMENT_KEYS))


class TestArchivos(unittest.TestCase):
    def setUp(self):
        sandbox.reset()

    def test_guardar_y_leer_conserva_todo(self):
        cfg = config.sanitize_config({"style": "x", "arm": 15, "monitor": "DP-2", "offset_y": -40})
        config.save_config(cfg)
        self.assertEqual(config.load_config(), cfg)

    def test_el_archivo_guardado_lleva_version(self):
        config.save_config(config.sanitize_config({}))
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        self.assertEqual(raw["version"], config.SCHEMA_VERSION)

    def test_un_archivo_danado_no_rompe_nada(self):
        CONFIG_FILE.write_text("{ esto no es json", encoding="utf-8")
        self.assertEqual(config.load_config(), config.DEFAULTS)

    def test_se_lee_el_formato_antiguo_sin_version(self):
        CONFIG_FILE.write_text(json.dumps({"style": "dot", "dot_radius": 5}), encoding="utf-8")
        cfg = config.load_config()
        self.assertEqual(cfg["style"], "dot")
        self.assertEqual(cfg["dot_radius"], 5)

    def test_la_escritura_es_atomica(self):
        """No debe quedar ningún archivo temporal suelto."""
        config.save_config(config.sanitize_config({}))
        self.assertEqual(list(CONFIG_FILE.parent.glob("*.tmp")), [])

    def test_los_presets_antiguos_se_migran(self):
        LEGACY_PROFILES_FILE.write_text(
            json.dumps({"Vieja": {"style": "dot", "dot_radius": 4}}), encoding="utf-8"
        )
        profiles = config.load_profiles()
        self.assertIn("Vieja", profiles)
        self.assertEqual(profiles["Vieja"]["dot_radius"], 4)
        self.assertTrue(PROFILES_FILE.is_file(), "debería haberse creado profiles.json")
        self.assertTrue(LEGACY_PROFILES_FILE.is_file(), "el archivo antiguo se conserva")

    def test_los_perfiles_nuevos_ganan_al_archivo_antiguo(self):
        LEGACY_PROFILES_FILE.write_text(json.dumps({"Vieja": {}}), encoding="utf-8")
        config.save_profiles({"Nueva": config.appearance(config.sanitize_config({}))})
        self.assertEqual(list(config.load_profiles()), ["Nueva"])

    def test_los_perfiles_guardados_pierden_la_posicion(self):
        config.save_profiles({"P": config.sanitize_config({"offset_x": 99, "monitor": "DP-1"})})
        self.assertNotIn("offset_x", config.load_profiles()["P"])


class TestRecorridoDePerfiles(unittest.TestCase):
    def setUp(self):
        sandbox.reset()

    def test_el_orden_pone_primero_los_incluidos(self):
        order = config.profile_order({"zeta": {}, "alfa": {}})
        self.assertEqual(order[:len(config.BUILTIN_PROFILES)], list(config.BUILTIN_PROFILES))
        self.assertEqual(order[-2:], ["alfa", "zeta"])

    def test_se_busca_sin_distinguir_mayusculas(self):
        found = config.profile_appearance("punto VERDE", {})
        self.assertIsNotNone(found)
        self.assertEqual(found[1], "Punto verde")

    def test_un_perfil_que_no_existe_da_none(self):
        self.assertIsNone(config.profile_appearance("no existe", {}))

    def test_el_siguiente_perfil_va_en_orden_y_da_la_vuelta(self):
        order = config.profile_order({})
        cfg = config.sanitize_config(config.BUILTIN_PROFILES[order[0]])
        self.assertEqual(config.next_profile_name(cfg, {}), order[1])
        ultimo = config.sanitize_config(config.BUILTIN_PROFILES[order[-1]])
        self.assertEqual(config.next_profile_name(ultimo, {}), order[0])

    def test_desde_una_mira_personalizada_salta_al_primero(self):
        cfg = config.sanitize_config({"arm": 37, "gap": 19, "thickness": 7})
        self.assertEqual(config.next_profile_name(cfg, {}), config.profile_order({})[0])

    def test_la_posicion_no_influye_en_el_recorrido(self):
        order = config.profile_order({})
        cfg = config.sanitize_config({**config.BUILTIN_PROFILES[order[0]], "offset_x": 120})
        self.assertEqual(config.next_profile_name(cfg, {}), order[1])


class TestLimpiezaDeImagenes(unittest.TestCase):
    def setUp(self):
        sandbox.reset()
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        for name in ("usada.png", "en-perfil.png", "huerfana.png"):
            (IMAGES_DIR / name).write_bytes(sandbox.png_bytes())

    def test_solo_se_borran_las_que_no_usa_nadie(self):
        cfg = config.sanitize_config({"style": "image", "image": "usada.png"})
        profiles = {"P": config.appearance(config.sanitize_config(
            {"style": "image", "image": "en-perfil.png"}))}
        config.remove_unused_images(cfg, profiles)
        quedan = sorted(p.name for p in IMAGES_DIR.glob("*.png"))
        self.assertEqual(quedan, ["en-perfil.png", "usada.png"])


if __name__ == "__main__":
    unittest.main()
