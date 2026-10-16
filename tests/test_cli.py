"""Línea de comandos: análisis de las opciones y lo que pasa cuando no hay
ninguna instancia en ejecución."""
import contextlib
import io
import unittest

import sandbox  # noqa: F401  (debe importarse primero)

from crosshair import cli, config


def run(*argv):
    """Ejecuta la línea de comandos y devuelve (código de salida, salida)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = cli.main(list(argv))
    return code, out.getvalue()


class TestOpciones(unittest.TestCase):
    def parse(self, *argv):
        return cli.build_parser().parse_args(list(argv))

    def test_sin_opciones_no_hay_orden(self):
        self.assertEqual(cli.requested_command(self.parse()), (None, None))

    def test_cada_opcion_da_su_orden(self):
        casos = {
            "--toggle": ("toggle", None),
            "--on": ("on", None),
            "--off": ("off", None),
            "--next-profile": ("next-profile", None),
            "--status": ("status", None),
            "--quit": ("quit", None),
        }
        for flag, expected in casos.items():
            with self.subTest(flag=flag):
                self.assertEqual(cli.requested_command(self.parse(flag)), expected)

    def test_el_perfil_lleva_su_nombre(self):
        self.assertEqual(cli.requested_command(self.parse("--profile", "Punto verde")),
                         ("profile", "Punto verde"))

    def test_el_perfil_gana_a_las_demas_ordenes(self):
        """Si se piden dos cosas a la vez, el perfil es la más concreta."""
        self.assertEqual(cli.requested_command(self.parse("--profile", "P", "--toggle"))[0], "profile")

    def test_una_opcion_que_no_existe_termina_con_error(self):
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                self.parse("--inventada")

    def test_version(self):
        with self.assertRaises(SystemExit) as caught:
            with contextlib.redirect_stdout(io.StringIO()):
                self.parse("--version")
        self.assertEqual(caught.exception.code, 0)


class TestSinInstancia(unittest.TestCase):
    """Sin ninguna instancia en ejecución, estas órdenes no deben abrir la interfaz."""

    def setUp(self):
        sandbox.reset()

    def test_listar_perfiles(self):
        code, out = run("--list-profiles")
        self.assertEqual(code, 0)
        for name in config.BUILTIN_PROFILES:
            self.assertIn(name, out)
        self.assertIn("*", out, "debería marcar el perfil que coincide con la mira actual")

    def test_desactivar_no_hace_nada(self):
        self.assertEqual(run("--off")[0], 0)

    def test_cerrar_no_hace_nada(self):
        self.assertEqual(run("--quit")[0], 0)

    def test_el_estado_avisa_de_que_no_esta_en_ejecucion(self):
        code, out = run("--status")
        self.assertEqual(code, 1)
        self.assertIn("no está en ejecución", out)

    def test_aplicar_un_perfil_escribe_la_configuracion(self):
        code, out = run("--profile", "Punto verde")
        self.assertEqual(code, 0)
        self.assertIn("Punto verde", out)
        self.assertEqual(config.load_config()["style"], "dot")

    def test_aplicar_un_perfil_respeta_la_posicion(self):
        config.save_config(config.sanitize_config({"offset_x": 42, "monitor": "DP-9"}))
        run("--profile", "Círculo cian")
        cfg = config.load_config()
        self.assertEqual(cfg["style"], "circle")
        self.assertEqual(cfg["offset_x"], 42)
        self.assertEqual(cfg["monitor"], "DP-9")

    def test_un_perfil_que_no_existe_da_error(self):
        code, out = run("--profile", "no existe")
        self.assertEqual(code, 1)
        self.assertIn("No existe", out)

    def test_el_perfil_siguiente_tambien_funciona(self):
        order = config.profile_order({})
        config.save_config(config.sanitize_config(config.BUILTIN_PROFILES[order[0]]))
        code, _out = run("--next-profile")
        self.assertEqual(code, 0)
        esperado = config.profile_appearance(order[1], {})[0]
        self.assertEqual(config.appearance(config.load_config()), esperado)


if __name__ == "__main__":
    unittest.main()
