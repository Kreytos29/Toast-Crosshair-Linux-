# Cambios

## 2.1.0

- La pestaña Ajustes detecta si usas `hyprland.lua` (Hyprland 0.55 o posterior)
  o `hyprland.conf`, y enseña las líneas del atajo en el formato que te toca.
  Un selector permite ver el otro. Nada del programa depende de la
  configuración de Hyprland: solo cambia el texto que se ofrece para copiar.
- Las líneas en Lua se generan con comillas seguras, así que una ruta con
  espacios o comillas no rompe el archivo.

## 2.0.0

Reorganización del proyecto y rediseño de la interfaz.

### Nuevo

- Estilos **cruz en T** y **aspa**, además de los que ya había.
- **Perfiles** (antes «presets») que se pueden **importar y exportar** como
  archivo. Si la mira es una imagen, el PNG viaja dentro del mismo archivo.
- **Inicio con la sesión** desde la pestaña Ajustes, sin tocar hyprland.conf.
- **Mapa de posición**: se arrastra la mira sobre un dibujo del monitor.
- Línea de comandos completa: `--profile`, `--next-profile`, `--list-profiles`,
  `--status`, `--quit` y `--debug`, además de `--toggle`, `--on` y `--off`.
- Iconos nuevos. El de la bandeja cambia de color según la mira esté activa.
- Pruebas automáticas: `python -m unittest discover -s tests`.
- `pyproject.toml`, archivo `.desktop`, icono instalable y borrador de PKGBUILD.

### Cambios

- La ventana se reorganizó en tres pestañas: Mira, Posición y Ajustes, con la
  vista previa más grande y un selector de estilo con dibujos.
- La geometría de la mira vive ahora en un solo sitio (`crosshair/geometry.py`)
  y la usan tanto el overlay (Cairo) como la vista previa (QPainter). Antes
  estaba duplicada y había que cambiar las dos a la vez.
- El programa es un paquete de Python. Se ejecuta con `python run.py` o, si se
  instala, con el comando `crosshair`. Las líneas para hyprland.conf de la
  pestaña Ajustes ya vienen con la ruta correcta.
- `config.json` y `profiles.json` guardan el número de versión del formato.
- Los mensajes van por el sistema de registro de Python, con `--debug`.

### Arreglos

- La mira se centra en el monitor completo y no en el hueco que dejan las
  barras. Con la barra lateral de Caelestia quedaba unos 25 px a la derecha.
- `--status` no respondía: la orden no estaba contemplada en el manejador.

### Migración desde 1.x

Los perfiles de `presets.json` se pasan solos a `profiles.json` la primera vez
que se abre el programa; el archivo antiguo se conserva. Hay que actualizar las
líneas de hyprland.conf, porque la ruta del programa cambió: cópialas de la
pestaña **Ajustes**.
