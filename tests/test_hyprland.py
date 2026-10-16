"""Líneas de configuración para Hyprland, en sus dos formatos."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import sandbox  # debe importarse primero: aísla la configuración del usuario

from crosshair import hyprland

# Simula la API de Hyprland para comprobar que el fragmento no solo es Lua
# válido, sino que llama a lo que debe con los argumentos que debe.
LUA_STUB = """
local log = {}
hl = {
  dsp = { exec_cmd = function(c) return {kind = "dispatcher", cmd = c} end },
  exec_cmd = function(c) log[#log+1] = "exec_cmd\\t" .. c end,
  on = function(ev, fn) log[#log+1] = "on\\t" .. ev; fn() end,
  bind = function(key, d) log[#log+1] = "bind\\t" .. key .. "\\t" .. d.cmd end,
  window_rule = function(t)
    log[#log+1] = ("rule\\t%s\\t%s\\t%s"):format(t.name, t.match.class, tostring(t.float))
  end,
}
dofile(arg[1])
for _, line in ipairs(log) do print(line) end
"""


def setUpModule():
    sandbox.reset()


def lua_binary():
    for name in ("lua5.4", "lua", "lua5.3"):
        path = shutil.which(name)
        if path:
            return path
    return None


class TestDeteccion(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="hypr-"))
        (self.tmp / "hypr").mkdir()
        self.real = hyprland.config_dir
        hyprland.config_dir = lambda: self.tmp / "hypr"

    def tearDown(self):
        hyprland.config_dir = self.real
        shutil.rmtree(self.tmp, ignore_errors=True)

    def touch(self, name):
        (self.tmp / "hypr" / name).write_text("", encoding="utf-8")

    def test_sin_configuracion(self):
        self.assertIsNone(hyprland.detect_flavour())

    def test_solo_conf(self):
        self.touch("hyprland.conf")
        self.assertEqual(hyprland.detect_flavour(), hyprland.CONF)

    def test_solo_lua(self):
        self.touch("hyprland.lua")
        self.assertEqual(hyprland.detect_flavour(), hyprland.LUA)

    def test_con_las_dos_gana_lua(self):
        """Es el mismo orden que sigue Hyprland al arrancar."""
        self.touch("hyprland.conf")
        self.touch("hyprland.lua")
        self.assertEqual(hyprland.detect_flavour(), hyprland.LUA)


class TestLineas(unittest.TestCase):
    ORDENES = ("crosshair", 'python "$HOME/mi carpeta/run.py"')

    def test_el_formato_clasico_lleva_lo_necesario(self):
        text = hyprland.conf_lines("crosshair")
        self.assertIn("exec-once = crosshair --hidden", text)
        self.assertIn("bind = SUPER, F10, exec, crosshair --toggle", text)
        self.assertIn("--next-profile", text)
        self.assertIn("windowrule", text)

    def test_los_dos_formatos_usan_las_mismas_ordenes(self):
        for command in self.ORDENES:
            lua, conf = hyprland.lua_lines(command), hyprland.conf_lines(command)
            for flag in ("--hidden", "--toggle", "--next-profile"):
                with self.subTest(command=command, flag=flag):
                    self.assertIn(f"{command} {flag}", lua)
                    self.assertIn(f"{command} {flag}", conf)

    def test_lines_elige_segun_el_formato(self):
        self.assertEqual(hyprland.lines(hyprland.LUA, "c"), hyprland.lua_lines("c"))
        self.assertEqual(hyprland.lines(hyprland.CONF, "c"), hyprland.conf_lines("c"))

    def test_la_explicacion_cambia_con_lo_detectado(self):
        self.assertIn("No encontré", hyprland.explanation(hyprland.LUA, None))
        self.assertIn("Encontré", hyprland.explanation(hyprland.LUA, hyprland.LUA))
        # Formato distinto del que tiene el usuario: hay que avisarlo
        aviso = hyprland.explanation(hyprland.LUA, hyprland.CONF)
        self.assertIn("hyprland.conf", aviso)
        self.assertIn("hyprland.lua", aviso)


class TestCadenasDeLua(unittest.TestCase):
    def test_sin_comillas_se_usan_comillas_normales(self):
        self.assertEqual(hyprland.lua_string("crosshair --toggle"), '"crosshair --toggle"')

    def test_con_comillas_se_usan_corchetes_largos(self):
        self.assertEqual(hyprland.lua_string('python "x.py"'), '[[python "x.py"]]')

    def test_si_el_texto_lleva_corchetes_se_sube_de_nivel(self):
        self.assertEqual(hyprland.lua_string('a ]] b "c"'), '[=[a ]] b "c"]=]')
        self.assertEqual(hyprland.lua_string('a ]] b ]=] c "d"'), '[==[a ]] b ]=] c "d"]==]')


@unittest.skipIf(lua_binary() is None, "hace falta un intérprete de Lua")
class TestLuaDeVerdad(unittest.TestCase):
    """Se ejecuta el fragmento con Lua y una API falsa de Hyprland, para
    comprobar que es válido y que las órdenes llegan enteras."""

    def run_snippet(self, command):
        tmp = Path(tempfile.mkdtemp(prefix="lua-"))
        try:
            (tmp / "stub.lua").write_text(LUA_STUB, encoding="utf-8")
            (tmp / "snippet.lua").write_text(hyprland.lua_lines(command), encoding="utf-8")
            done = subprocess.run(
                [lua_binary(), str(tmp / "stub.lua"), str(tmp / "snippet.lua")],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(done.returncode, 0, done.stderr)
            return [line.split("\t") for line in done.stdout.splitlines()]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_una_orden_sencilla(self):
        rows = self.run_snippet("crosshair")
        self.assertEqual(rows, [
            ["on", "hyprland.start"],
            ["exec_cmd", "crosshair --hidden"],
            ["bind", "SUPER + F10", "crosshair --toggle"],
            ["bind", "SUPER + SHIFT + F10", "crosshair --next-profile"],
            ["rule", "crosshair-float", "^(crosshair)$", "true"],
        ])

    def test_una_ruta_con_comillas_y_espacios(self):
        command = 'python "$HOME/mi carpeta/run.py"'
        rows = self.run_snippet(command)
        self.assertEqual(rows[1], ["exec_cmd", f"{command} --hidden"])
        self.assertEqual(rows[2], ["bind", "SUPER + F10", f"{command} --toggle"])


if __name__ == "__main__":
    unittest.main()
