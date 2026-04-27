import os
import sys
import shutil
from pathlib import Path


APP_DIR_NAME = "NucleiGUI"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    if is_frozen():
        executable = Path(sys.executable).resolve()
        if sys.platform == "darwin":
            for parent in executable.parents:
                if parent.suffix == ".app":
                    return parent.parent
        return executable.parent
    return Path(__file__).resolve().parents[1]


def resource_root() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).resolve()
    return app_dir()


def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)


def external_path(*parts: str) -> Path:
    return app_dir().joinpath(*parts)


def user_data_dir(create: bool = True) -> Path:
    override = os.environ.get("NUCLEI_GUI_DATA_DIR")
    if override:
        base = Path(override)
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / APP_DIR_NAME
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / APP_DIR_NAME

    if create:
        base.mkdir(parents=True, exist_ok=True)
    return base


def user_data_path(*parts: str, create_parent: bool = True) -> Path:
    path = user_data_dir(create=True).joinpath(*parts)
    if create_parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    return path


def log_dir() -> Path:
    path = user_data_path("logs", create_parent=True)
    path.mkdir(parents=True, exist_ok=True)
    return path


def legacy_project_path(*parts: str) -> Path:
    return Path(__file__).resolve().parents[1].joinpath(*parts)


def database_path(filename: str) -> Path:
    target = user_data_path(filename, create_parent=True)
    legacy = legacy_project_path(filename)
    if not target.exists() and legacy.exists():
        try:
            shutil.copy2(legacy, target)
        except OSError:
            pass
    return target


def ensure_external_layout() -> None:
    external_path("bin").mkdir(parents=True, exist_ok=True)
    poc_root = external_path("poc_library")
    for child in ("custom", "cloud", "user_generated"):
        poc_root.joinpath(child).mkdir(parents=True, exist_ok=True)
