#!/usr/bin/env python3
"""Ejecuta Crosshair sin instalarlo.

    python run.py              abre la ventana de ajustes
    python run.py --toggle     activa o desactiva la mira
    python run.py --help       todas las opciones

Si lo instalas (con ./install.sh o el paquete de tu distribución) puedes usar
directamente el comando «crosshair».
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crosshair.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
