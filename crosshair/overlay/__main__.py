"""Proceso del overlay: python -m crosshair.overlay

Normalmente lo lanza la ventana de ajustes, pero también se puede ejecutar a
mano para ver la mira sin la bandeja ni los ajustes.
"""
import sys

from .window import main

if __name__ == "__main__":
    sys.exit(main())
