"""Aísla las pruebas de la configuración real del usuario.

Hay que importarlo ANTES que cualquier módulo de crosshair: las rutas se
calculan al importar crosshair.paths, así que las variables de entorno tienen
que estar puestas antes.
"""
import atexit
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Las pruebas provocan a propósito errores que el programa registra; sin esto,
# la salida se llena de avisos esperados
logging.disable(logging.WARNING)

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

TMP = Path(tempfile.mkdtemp(prefix="crosshair-tests-"))
os.environ["XDG_CONFIG_HOME"] = str(TMP / "config")
os.environ["XDG_RUNTIME_DIR"] = str(TMP / "run")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
(TMP / "run").mkdir(parents=True, exist_ok=True)
os.chmod(TMP / "run", 0o700)

atexit.register(lambda: shutil.rmtree(TMP, ignore_errors=True))


def reset():
    """Deja la carpeta de configuración vacía antes de cada prueba."""
    from crosshair.paths import CONFIG_DIR

    shutil.rmtree(CONFIG_DIR, ignore_errors=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def png_bytes(size=8):
    """Un PNG mínimo y válido, para las pruebas que necesitan una imagen."""
    import struct
    import zlib

    raw = b"".join(b"\x00" + bytes([255, 0, 0, 255] * size) for _ in range(size))

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))
