#!/usr/bin/env bash
# Instalador de Crosshair para Linux.
#
# Qué hace:
#   1. Comprueba que haya python3 (>= 3.10) y que existan las bibliotecas que
#      usa el programa (PyQt6, PyGObject, pycairo y gtk4-layer-shell). No
#      instala nada del sistema: si falta algo te dice con qué comando.
#   2. Copia el programa a ~/.local/share/crosshair, así sigue funcionando
#      aunque borres esta carpeta. Tus ajustes NO viven ahí sino en
#      ~/.config/crosshair, así que actualizar nunca los pisa.
#   3. Crea el comando «crosshair» en ~/.local/bin, el icono y la entrada del
#      menú de aplicaciones.
#
# Uso:
#   ./install.sh               instala o actualiza
#   ./install.sh --uninstall   desinstala (ver ./uninstall.sh --help)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
INSTALL_DIR="$DATA_HOME/crosshair"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
DESKTOP_DIR="$DATA_HOME/applications"
ICON_DIR="$DATA_HOME/icons/hicolor/scalable/apps"
LAUNCHER="$BIN_DIR/crosshair"
DESKTOP_FILE="$DESKTOP_DIR/crosshair.desktop"
ICON_FILE="$ICON_DIR/crosshair.svg"
AUTOSTART_FILE="$CONFIG_HOME/autostart/crosshair.desktop"
USER_CONFIG_DIR="$CONFIG_HOME/crosshair"

c_green="\033[0;32m"; c_yellow="\033[0;33m"; c_red="\033[0;31m"; c_reset="\033[0m"
info()  { echo -e "${c_green}==>${c_reset} $1"; }
warn()  { echo -e "${c_yellow}⚠${c_reset}  $1"; }
error() { echo -e "${c_red}✗${c_reset} $1" >&2; }

refresh_caches() {
    command -v update-desktop-database >/dev/null 2>&1 && \
        update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
    command -v gtk-update-icon-cache >/dev/null 2>&1 && \
        gtk-update-icon-cache -q -t "$DATA_HOME/icons/hicolor" >/dev/null 2>&1 || true
}

uninstall() {
    shift || true
    local all=0 yes=0
    for arg in "$@"; do
        case "$arg" in
            --todo) all=1 ;;
            --yes|-y) yes=1 ;;
            -h|--help)
                cat <<EOF
Uso: ./uninstall.sh [--todo] [--yes]

Quita el comando, el icono, la entrada del menú, el inicio automático y el
programa instalado. Tus perfiles y ajustes ($USER_CONFIG_DIR)
se conservan, salvo que pases --todo.
  --todo   borra también los ajustes, perfiles e imágenes importadas
  --yes    no pregunta nada
EOF
                exit 0 ;;
            *) error "Opción desconocida: $arg"; exit 2 ;;
        esac
    done

    info "Desinstalando Crosshair..."
    # Cierra la instancia en ejecución para que no quede la mira en pantalla.
    if [ -x "$LAUNCHER" ]; then
        "$LAUNCHER" --quit >/dev/null 2>&1 || true
    fi
    rm -f "$LAUNCHER" "$DESKTOP_FILE" "$ICON_FILE" "$AUTOSTART_FILE"
    rm -rf "$INSTALL_DIR"

    if [ -d "$USER_CONFIG_DIR" ]; then
        if [ "$all" -eq 0 ] && [ "$yes" -eq 0 ] && [ -t 0 ]; then
            read -r -p "¿Borrar también tus ajustes y perfiles ($USER_CONFIG_DIR)? [y/N] " reply
            case "$reply" in [yY]*) all=1 ;; esac
        fi
        if [ "$all" -eq 1 ]; then
            rm -rf "$USER_CONFIG_DIR"
            info "Ajustes y perfiles borrados."
        else
            info "Se conservaron tus ajustes en $USER_CONFIG_DIR."
        fi
    fi
    refresh_caches
    info "Listo. Crosshair desinstalado."
    exit 0
}

case "${1:-}" in
    --uninstall) uninstall "$@" ;;
    -h|--help)
        echo "Uso: ./install.sh [--uninstall]"; exit 0 ;;
    "") ;;
    *) error "Opción desconocida: $1"; exit 2 ;;
esac

# --- 1. python3 y bibliotecas --------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
    error "No se encontró python3. Instálalo con el gestor de paquetes de tu"
    error "distribución (por ejemplo 'sudo pacman -S python') y vuelve a correr este script."
    exit 1
fi
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
    error "Crosshair necesita Python 3.10 o posterior (tienes $(python3 -V 2>&1))."
    exit 1
fi

missing=()
python3 -c 'import PyQt6.QtWidgets' 2>/dev/null || missing+=("PyQt6 (ventana de ajustes y bandeja)")
python3 -c 'import gi' 2>/dev/null || missing+=("PyGObject")
python3 -c 'import cairo' 2>/dev/null || missing+=("pycairo")
if python3 -c 'import gi' 2>/dev/null; then
    python3 -c 'import gi; gi.require_version("Gtk", "4.0")' 2>/dev/null || missing+=("GTK4")
    python3 -c 'import gi; gi.require_version("Gtk4LayerShell", "1.0")' 2>/dev/null || missing+=("gtk4-layer-shell")
fi
if [ "${#missing[@]}" -gt 0 ]; then
    warn "Faltan estas dependencias del sistema:"
    for m in "${missing[@]}"; do echo "     - $m"; done
    echo "   Arch:   sudo pacman -S python-pyqt6 python-gobject python-cairo gtk4 gtk4-layer-shell"
    echo "   Debian/Ubuntu: sudo apt install python3-pyqt6 python3-gi python3-gi-cairo libgtk-4-1"
    echo "                  (gtk4-layer-shell hay que compilarlo: github.com/wmww/gtk4-layer-shell)"
    echo "   Se instala igual, pero no arrancará hasta que las instales."
fi

# --- 2. copiar el programa -----------------------------------------------
info "Instalando en $INSTALL_DIR ..."
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -r "$SCRIPT_DIR/crosshair" "$INSTALL_DIR/crosshair"
cp "$SCRIPT_DIR/run.py" "$SCRIPT_DIR/LICENSE" "$SCRIPT_DIR/install.sh" "$SCRIPT_DIR/uninstall.sh" "$INSTALL_DIR/"
find "$INSTALL_DIR" -name __pycache__ -type d -prune -exec rm -rf {} +

# --- 3. comando, icono y menú --------------------------------------------
mkdir -p "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec python3 "$INSTALL_DIR/run.py" "\$@"
EOF
chmod +x "$LAUNCHER"

install -m644 "$SCRIPT_DIR/data/icons/crosshair.svg" "$ICON_FILE"
# En el .desktop el comando va con ruta absoluta: el menú no siempre tiene
# ~/.local/bin en el PATH.
sed "s#^Exec=crosshair#Exec=$LAUNCHER#" "$SCRIPT_DIR/data/crosshair.desktop" > "$DESKTOP_FILE"
chmod 644 "$DESKTOP_FILE"
refresh_caches

info "Listo. Crosshair instalado."
echo "   Ábrelo desde el menú de aplicaciones o con:  crosshair"
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) warn "$BIN_DIR no está en tu PATH; añádelo para usar el comando 'crosshair'." ;;
esac
echo "   Desinstalar:  ./uninstall.sh   (o $INSTALL_DIR/uninstall.sh)"
