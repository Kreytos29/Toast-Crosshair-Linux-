"""Línea de comandos.

Las órdenes que se mandan a una instancia en ejecución se resuelven antes de
importar Qt, así que un atajo de teclado responde al instante.
"""
import argparse
import logging
import sys

from . import __version__, config, ipc

# Opción de la línea de comandos -> orden que entiende la instancia en ejecución
FLAG_COMMANDS = {
    "toggle": "toggle",
    "on": "on",
    "off": "off",
    "next_profile": "next-profile",
    "status": "status",
    "quit": "quit",
}


def build_parser():
    parser = argparse.ArgumentParser(
        prog="crosshair",
        description="Mira para juegos en Linux. Sin opciones, abre la ventana de ajustes.",
        epilog="Solo se ejecuta una instancia: las demás le mandan la orden y terminan.",
    )
    parser.add_argument("--hidden", action="store_true", help="iniciar solo en la bandeja, sin abrir la ventana")
    parser.add_argument("--debug", action="store_true", help="mostrar mensajes detallados en la terminal")
    parser.add_argument("--version", action="version", version=f"Crosshair {__version__}")

    group = parser.add_argument_group("mira")
    group.add_argument("--toggle", action="store_true", help="activar o desactivar la mira")
    group.add_argument("--on", action="store_true", help="activar la mira")
    group.add_argument("--off", action="store_true", help="desactivar la mira")

    group = parser.add_argument_group("perfiles")
    group.add_argument("--profile", metavar="NOMBRE", help="aplicar un perfil por su nombre")
    group.add_argument("--next-profile", action="store_true", help="pasar al perfil siguiente")
    group.add_argument("--list-profiles", action="store_true", help="listar los perfiles y terminar")

    group = parser.add_argument_group("estado")
    group.add_argument("--status", action="store_true", help="mostrar el estado de la instancia en ejecución")
    group.add_argument("--quit", action="store_true", help="cerrar la instancia en ejecución")
    return parser


def setup_logging(debug):
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s" if debug else "crosshair: %(message)s",
        stream=sys.stderr,
    )


def requested_command(args):
    """(orden, argumento) según las opciones, o (None, None)."""
    if args.profile:
        return "profile", args.profile
    for attribute, command in FLAG_COMMANDS.items():
        if getattr(args, attribute):
            return command, None
    return None, None


def list_profiles():
    profiles = config.load_profiles()
    current = config.appearance(config.load_config())
    for name in config.profile_order(profiles):
        found = config.profile_appearance(name, profiles)
        mark = "*" if found and found[0] == current else " "
        kind = "incluido" if name in config.BUILTIN_PROFILES else "propio"
        print(f"{mark} {name}  ({kind})")
    return 0


def apply_profile_offline(name):
    """Aplica un perfil escribiendo config.json, sin que haya ninguna instancia
    en ejecución. La posición de la mira no cambia."""
    profiles = config.load_profiles()
    cfg = config.load_config()
    if name is None:
        name = config.next_profile_name(cfg, profiles)
    found = config.profile_appearance(name, profiles) if name else None
    if found is None:
        print(f"No existe el perfil «{name}».", file=sys.stderr)
        return 1
    look, real_name = found
    config.save_config({**look, **config.placement(cfg)})
    print(f"Perfil «{real_name}» aplicado. Crosshair no está en ejecución; se usará al iniciarlo.")
    return 0


def print_status(reply):
    if reply is None:
        print("Crosshair no está en ejecución.")
        return 1
    if not reply.get("ok", True) or "version" not in reply:
        print(reply.get("error", "La instancia en ejecución no respondió al estado."), file=sys.stderr)
        return 1
    print(f"Estado:   en ejecución (versión {reply.get('version', '?')})")
    print(f"Mira:     {'activa' if reply.get('overlay') else 'inactiva'}")
    print(f"Perfil:   {reply.get('profile') or 'personalizado'}")
    print(f"Monitor:  {reply.get('monitor') or 'automático'}")
    print(f"Posición: X {reply.get('offset_x', 0):+d} px, Y {reply.get('offset_y', 0):+d} px")
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    setup_logging(args.debug)

    if args.list_profiles:
        return list_profiles()

    command, argument = requested_command(args)

    # Primero se intenta con la instancia en ejecución
    reply = ipc.send(command or ("ping" if args.hidden else "show"), argument)

    if command == "status":
        return print_status(reply)

    if reply is not None:
        if not reply.get("ok", True):
            print(reply.get("error", "La orden no se pudo aplicar."), file=sys.stderr)
            return 1
        if command == "profile":
            print(f"Perfil «{reply.get('profile')}» aplicado.")
        return 0

    # No hay ninguna instancia en ejecución
    if command in ("off", "quit"):
        return 0
    if command in ("profile", "next-profile"):
        return apply_profile_offline(argument)

    from .ui.app import run
    return run(hidden=args.hidden or command in ("toggle", "on"), debug=args.debug)
