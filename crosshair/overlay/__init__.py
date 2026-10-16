"""Proceso del overlay: dibuja la mira encima de todas las ventanas.

Este paquete se mantiene vacío a propósito. gtk4-layer-shell exige cargar su
biblioteca antes de importar Gtk, y eso se hace en crosshair.overlay.render y
crosshair.overlay.window, no al importar el paquete.
"""
