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
            echo "Usage: bash build_package_linux.sh [--skip-install] [--skip-build] [--no-archive]"
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

sync_runtime_layout() {
    local target_dir="$1"
    mkdir -p "$target_dir/bin"
    mkdir -p "$target_dir/poc_library/custom"
    mkdir -p "$target_dir/poc_library/cloud"
    mkdir -p "$target_dir/poc_library/user_generated"

    local nuclei_binary="$ROOT/bin/nuclei_linux"
    if [ -f "$nuclei_binary" ]; then
        cp "$nuclei_binary" "$target_dir/bin/nuclei_linux"
        chmod +x "$target_dir/bin/nuclei_linux"
    fi

    if [ -d "$ROOT/poc_library" ]; then
        cp -R "$ROOT/poc_library/." "$target_dir/poc_library/"
    fi
}

if [ "$SKIP_INSTALL" -eq 0 ]; then
    "$PYTHON_BIN" -m pip install -r "requirements.txt"
    "$PYTHON_BIN" -m pip install -r "requirements-build.txt"
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
        "main.py"
fi

APP_PATH="$ROOT/dist/Nuclei_GUI"
if [ ! -f "$APP_PATH" ]; then
    echo "Build output not found: $APP_PATH" >&2
    exit 1
fi

PACKAGE_DIR="$ROOT/dist/Nuclei_GUI_linux_portable"
rm -rf "$PACKAGE_DIR"

cp "$APP_PATH" "$PACKAGE_DIR/Nuclei_GUI"
chmod +x "$PACKAGE_DIR/Nuclei_GUI"
sync_runtime_layout "$ROOT/dist"
sync_runtime_layout "$PACKAGE_DIR"

if [ "$CREATE_ARCHIVE" -eq 1 ]; then
    VERSION="$("$PYTHON_BIN" - <<'PY'
from pathlib import Path
import re

text = Path("core/version.py").read_text(encoding="utf-8")
match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
print(match.group(1) if match else "unknown")
PY
)"
    ARCHIVE_PATH="$ROOT/dist/Nuclei_GUI_linux_portable_v${VERSION}.tar.gz"
    tar -czf "$ARCHIVE_PATH" -C "$ROOT/dist" "Nuclei_GUI_linux_portable"
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
echo "  Nuclei_GUI"
echo "  bin/nuclei_linux"
echo "  poc_library/"
