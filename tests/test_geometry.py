"""La forma de la mira: la comparten el overlay y la vista previa, así que si
esto se rompe se rompen los dos a la vez."""
import math
import unittest

import sandbox  # debe importarse primero: aísla la configuración del usuario

from crosshair.config import sanitize_config
from crosshair.geometry import ARM_ANGLES, Disc, Polygon, Ring, radius, shapes


def setUpModule():
    sandbox.reset()


def bbox(points):
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    return min(xs), min(ys), max(xs), max(ys)


class TestShapes(unittest.TestCase):
    def test_cada_estilo_da_las_formas_esperadas(self):
        esperado = {
            "cross": (4, 1),    # cuatro brazos y un punto central
            "tcross": (3, 1),
            "x": (4, 1),
            "dot": (0, 1),
            "circle": (0, 2),   # el anillo y el punto central
            "image": (0, 0),
        }
        for style, (bars, others) in esperado.items():
            # El estilo imagen se pone a mano: sanitize_config vuelve a la cruz
            # mientras no haya un PNG de verdad en images/
            cfg = dict(sanitize_config({"center_dot": True}), style=style)
            items = shapes(cfg, 0)
            with self.subTest(style=style):
                self.assertEqual(sum(isinstance(i, Polygon) for i in items), bars)
                self.assertEqual(len(items) - bars, others)

    def test_el_brazo_derecho_coincide_con_la_formula_de_siempre(self):
        """Con grosor par el brazo va de gap a gap+arm, centrado en el eje."""
        cfg = sanitize_config({"style": "cross", "thickness": 2, "arm": 10, "gap": 4})
        x0, y0, x1, y1 = bbox(shapes(cfg, 0)[0].points)
        self.assertAlmostEqual(x0, 4.0)
        self.assertAlmostEqual(x1, 14.0)
        self.assertAlmostEqual(y0, -1.0)
        self.assertAlmostEqual(y1, 1.0)

    def test_el_grosor_impar_se_corre_medio_pixel(self):
        """Así las líneas caen sobre la rejilla de píxeles y no salen borrosas.
        Con grosor 3 el brazo derecho va de y = -1 a y = 2, no de -1,5 a 1,5."""
        impar = sanitize_config({"style": "cross", "thickness": 3, "center_dot": True})
        par = sanitize_config({"style": "cross", "thickness": 2, "center_dot": True})
        self.assertEqual(bbox(shapes(impar, 0)[0].points)[1::2], (-1.0, 2.0))
        self.assertEqual(bbox(shapes(par, 0)[0].points)[1::2], (-1.0, 1.0))
        # El punto central se corre junto con los brazos
        self.assertEqual([i for i in shapes(impar, 0) if isinstance(i, Disc)][0].cx, 0.5)
        self.assertEqual([i for i in shapes(par, 0) if isinstance(i, Disc)][0].cx, 0.0)

    def test_sin_desplazamiento_en_los_estilos_diagonales(self):
        """En el aspa, correr medio píxel no ayuda: las líneas son diagonales."""
        cfg = sanitize_config({"style": "x", "thickness": 3})
        disc = [i for i in shapes(cfg, 0) if isinstance(i, Disc)][0]
        self.assertEqual((disc.cx, disc.cy), (0.0, 0.0))

    def test_el_contorno_crece_por_los_cuatro_lados(self):
        cfg = sanitize_config({"style": "cross", "thickness": 2, "arm": 10, "gap": 4})
        x0, y0, x1, y1 = bbox(shapes(cfg, 2)[0].points)
        self.assertAlmostEqual(x0, 2.0)    # 4 - 2
        self.assertAlmostEqual(x1, 16.0)   # 14 + 2
        self.assertAlmostEqual(y0, -3.0)   # -1 - 2
        self.assertAlmostEqual(y1, 3.0)

    def test_los_brazos_apuntan_a_donde_toca(self):
        """0 grados es a la derecha y 90 hacia arriba (la Y de pantalla baja)."""
        for style, angles in ARM_ANGLES.items():
            cfg = sanitize_config({"style": style, "center_dot": False})
            bars = [i for i in shapes(cfg, 0) if isinstance(i, Polygon)]
            found = set()
            for bar in bars:
                cx = sum(x for x, _ in bar.points) / 4
                cy = sum(y for _, y in bar.points) / 4
                found.add(round(math.degrees(math.atan2(-cy, cx))) % 360)
            with self.subTest(style=style):
                self.assertEqual(found, set(angles))

    def test_la_cruz_en_t_no_tiene_brazo_arriba(self):
        cfg = sanitize_config({"style": "tcross", "center_dot": False})
        for bar in shapes(cfg, 0):
            cy = sum(y for _, y in bar.points) / 4
            self.assertGreaterEqual(cy, -0.001, "no debería haber nada por encima del centro")

    def test_el_anillo_se_vuelve_macizo_si_el_hueco_desaparece(self):
        cfg = sanitize_config({"style": "circle", "circle_radius": 4, "thickness": 8})
        ring = [i for i in shapes(cfg, 2) if isinstance(i, Ring)][0]
        self.assertLessEqual(ring.inner, 0)

    def test_el_radio_crece_con_el_contorno(self):
        cfg = sanitize_config({"style": "cross"})
        self.assertGreater(radius(cfg, 2), radius(cfg, 0))

    def test_el_radio_de_una_imagen_es_la_mitad_de_su_lado(self):
        cfg = dict(sanitize_config({}), style="image", image_size=80)
        self.assertEqual(radius(cfg), 40)


if __name__ == "__main__":
    unittest.main()
