"""Importar y exportar una mira como archivo."""
import json
import unittest

import sandbox  # noqa: F401  (debe importarse primero)

from crosshair import config, share
from crosshair.paths import IMAGES_DIR


class TestExportarImportar(unittest.TestCase):
    def setUp(self):
        sandbox.reset()
        self.path = sandbox.TMP / "prueba.crosshair.json"
        self.path.unlink(missing_ok=True)

    def test_ida_y_vuelta_conserva_el_aspecto(self):
        cfg = config.sanitize_config({"style": "x", "arm": 17, "gap": 7, "color": [0, 1, 0, 0.5]})
        share.export_to(self.path, cfg, "La mía")
        look, name = share.import_from(self.path)
        self.assertEqual(look, config.appearance(cfg))
        self.assertEqual(name, "La mía")

    def test_la_posicion_no_se_exporta(self):
        cfg = config.sanitize_config({"offset_x": 120, "monitor": "DP-3"})
        share.export_to(self.path, cfg, "P")
        data = json.loads(self.path.read_text(encoding="utf-8"))
        for key in config.PLACEMENT_KEYS:
            self.assertNotIn(key, data["crosshair"])

    def test_se_le_pone_la_extension_si_falta(self):
        path = share.export_to(sandbox.TMP / "sinextension", config.sanitize_config({}), "P")
        self.assertTrue(str(path).endswith(".json"))
        path.unlink()

    def test_la_imagen_viaja_dentro_del_archivo(self):
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        (IMAGES_DIR / "mia.png").write_bytes(sandbox.png_bytes())
        cfg = config.sanitize_config({"style": "image", "image": "mia.png", "image_size": 90})
        self.assertEqual(cfg["style"], "image")
        share.export_to(self.path, cfg, "Con imagen")

        # Se borra el original: la importación debe reconstruirlo desde el archivo
        (IMAGES_DIR / "mia.png").unlink()
        look, _name = share.import_from(self.path)
        self.assertEqual(look["style"], "image")
        self.assertEqual(look["image_size"], 90)
        self.assertTrue(config.image_path(look["image"]), "el PNG debería estar otra vez en images/")

    def test_la_imagen_importada_no_pisa_a_otra(self):
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        (IMAGES_DIR / "mia.png").write_bytes(sandbox.png_bytes())
        cfg = config.sanitize_config({"style": "image", "image": "mia.png"})
        share.export_to(self.path, cfg, "Con imagen")
        look, _name = share.import_from(self.path)
        self.assertNotEqual(look["image"], "mia.png")
        self.assertTrue((IMAGES_DIR / "mia.png").is_file(), "la original sigue ahí")


class TestArchivosMalos(unittest.TestCase):
    def setUp(self):
        sandbox.reset()
        self.path = sandbox.TMP / "malo.json"

    def _error(self, contenido):
        self.path.write_text(contenido, encoding="utf-8")
        with self.assertRaises(share.ShareError):
            share.import_from(self.path)

    def test_no_es_json(self):
        self._error("{{{ nada de esto")

    def test_no_lleva_mira_dentro(self):
        self._error(json.dumps({"app": "crosshair", "version": 2}))

    def test_no_es_un_diccionario(self):
        self._error(json.dumps([1, 2, 3]))

    def test_el_archivo_no_existe(self):
        with self.assertRaises(share.ShareError):
            share.import_from(sandbox.TMP / "no-existe.json")

    def test_la_imagen_incluida_no_es_un_png(self):
        import base64
        self._error(json.dumps({
            "crosshair": {"style": "image"},
            "image": {"name": "x", "png_base64": base64.b64encode(b"GIF89a esto no").decode()},
        }))

    def test_la_imagen_incluida_esta_rota(self):
        self._error(json.dumps({
            "crosshair": {"style": "image"},
            "image": {"name": "x", "png_base64": "no-es-base64-valido!!!"},
        }))

    def test_una_mira_con_valores_imposibles_se_corrige(self):
        self.path.write_text(json.dumps({
            "crosshair": {"style": "banana", "thickness": 9999, "color": "rojo"}
        }), encoding="utf-8")
        look, _name = share.import_from(self.path)
        self.assertEqual(look["style"], "cross")
        self.assertEqual(look["thickness"], config.LIMITS["thickness"][1])
        self.assertEqual(look["color"], config.DEFAULTS["color"])


class TestNombres(unittest.TestCase):
    def test_se_quitan_los_caracteres_raros_y_las_rutas(self):
        self.assertEqual(share.safe_stem("../../etc/passwd"), "passwd")
        self.assertEqual(share.safe_stem("mi mira ©2026.png"), "mi-mira-2026")
        self.assertEqual(share.safe_stem("///"), "mira")
        self.assertLessEqual(len(share.safe_stem("x" * 200)), 40)


if __name__ == "__main__":
    unittest.main()
