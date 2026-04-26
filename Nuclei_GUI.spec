# -*- mode: python ; coding: utf-8 -*-
import os


def prepare_windows_icon():
    ico_path = os.path.join("resources", "icon.ico")
    if os.path.exists(ico_path):
        return ico_path

    png_path = os.path.join("resources", "icon.png")
    generated_ico = os.path.join("build", "generated", "icon.ico")
    if not os.path.exists(png_path):
        return None

    os.makedirs(os.path.dirname(generated_ico), exist_ok=True)
    try:
        from PyQt5.QtGui import QImage

        image = QImage(png_path)
        if not image.isNull() and image.save(generated_ico, "ICO"):
            return generated_ico
    except Exception:
        pass

    # PyInstaller can also try image conversion if Pillow is available.
    return png_path


datas = [
    ("i18n/*.json", "i18n"),
    ("resources/*", "resources"),
]

hiddenimports = [
    "download_nuclei_with_progress",
]

icon_path = prepare_windows_icon()

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Nuclei_GUI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)
