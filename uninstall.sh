#!/usr/bin/env bash
# Desinstala Crosshair. Hace lo mismo que "./install.sh --uninstall".
#
# Uso:
#   ./uninstall.sh            pregunta si borrar también tus ajustes
#   ./uninstall.sh --todo     borra también ajustes, perfiles e imágenes
#   ./uninstall.sh --yes      no pregunta y conserva tus ajustes
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "$SCRIPT_DIR/install.sh" ]; then
    echo "No se encontró install.sh junto a este script (se buscó en $SCRIPT_DIR)." >&2
    exit 1
fi

exec "$SCRIPT_DIR/install.sh" --uninstall "$@"
