#!/usr/bin/env bash
set -euo pipefail

SKIP_INSTALL=0
SKIP_BUILD=0
CREATE_ARCHIVE=1

for arg in "$@"; do
    case "$arg" in
        --skip-install)
            SKIP_INSTALL=1
            ;;
        --skip-build)
            SKIP_BUILD=1
            ;;
        --no-archive)
            CREATE_ARCHIVE=0
            ;;
        -h|--help)
            echo "Usage: bash build_package_macos.sh [--skip-install] [--skip-build] [--no-archive]"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg" >&2
            exit 1
            ;;
    esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ "$SKIP_INSTALL" -eq 0 ]; then
    "$PYTHON_BIN" -m pip install -r "requirements.txt"
    "$PYTHON_BIN" -m pip install -r "requirements-build.txt"
fi

ICON_ARGS=()
if [ -f "$ROOT/resources/icon.icns" ]; then
    ICON_ARGS=(--icon "$ROOT/resources/icon.icns")
fi

if [ "$SKIP_BUILD" -eq 0 ]; then
    "$PYTHON_BIN" -m PyInstaller \
        --noconfirm \
        --clean \
        --onefile \
        --windowed \
        --name "Nuclei_GUI" \
        --add-data "i18n:i18n" \
        --add-data "resources:resources" \
        --hidden-import "download_nuclei_with_progress" \
        "${ICON_ARGS[@]}" \
        "main.py"
fi

APP_PATH="$ROOT/dist/Nuclei_GUI.app"
if [ ! -d "$APP_PATH" ]; then
    echo "Build output not found: $APP_PATH" >&2
    exit 1
fi

PACKAGE_DIR="$ROOT/dist/Nuclei_GUI_macos_portable"
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR/bin"
mkdir -p "$PACKAGE_DIR/poc_library/custom"
mkdir -p "$PACKAGE_DIR/poc_library/cloud"
mkdir -p "$PACKAGE_DIR/poc_library/user_generated"

cp -R "$APP_PATH" "$PACKAGE_DIR/Nuclei_GUI.app"

NUCLEI_BINARY="$ROOT/bin/nuclei_darwin"
if [ -f "$NUCLEI_BINARY" ]; then
    cp "$NUCLEI_BINARY" "$PACKAGE_DIR/bin/nuclei_darwin"
    chmod +x "$PACKAGE_DIR/bin/nuclei_darwin"
fi

if [ -d "$ROOT/poc_library" ]; then
    cp -R "$ROOT/poc_library/." "$PACKAGE_DIR/poc_library/"
fi

if [ "$CREATE_ARCHIVE" -eq 1 ]; then
    VERSION="$("$PYTHON_BIN" - <<'PY'
from pathlib import Path
import re

text = Path("core/version.py").read_text(encoding="utf-8")
match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
print(match.group(1) if match else "unknown")
PY
)"
    ARCHIVE_PATH="$ROOT/dist/Nuclei_GUI_macos_portable_v${VERSION}.zip"
    (cd "$ROOT/dist" && ditto -c -k --sequesterRsrc --keepParent "Nuclei_GUI_macos_portable" "$ARCHIVE_PATH")
fi

echo ""
echo "Package ready:"
echo "  $PACKAGE_DIR"
if [ "$CREATE_ARCHIVE" -eq 1 ]; then
    echo "Archive ready:"
    echo "  $ARCHIVE_PATH"
fi
echo ""
echo "External runtime layout:"
echo "  Nuclei_GUI.app"
echo "  bin/nuclei_darwin"
echo "  poc_library/"
