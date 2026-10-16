"""Crosshair: una mira para juegos en Linux.

El programa son dos procesos a propósito, porque GTK4 no tiene API de bandeja
y no conviene mezclar GTK con Qt en el mismo proceso:

  crosshair.overlay  GTK4 + gtk4-layer-shell. Dibuja la mira encima de todo y
                     deja pasar los clics. Vigila config.json y se actualiza solo.
  crosshair.ui       PyQt6. Icono en la bandeja y ventana de ajustes. Lanza y
                     detiene el overlay como proceso aparte.

Los dos comparten crosshair.geometry (la forma de la mira) y crosshair.config
(los valores y su validación).
"""

__version__ = "2.1.0"
__author__ = "@Kreytos29"
