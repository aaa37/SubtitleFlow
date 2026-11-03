import os
import sys
from pathlib import Path


def resource_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))


def data_root() -> Path:
    if override := os.environ.get("SUBTITLEFLOW_HOME"):
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "SubtitleFlow"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/SubtitleFlow"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "SubtitleFlow"


def bundled_tool(name: str) -> Path:
    suffix = ".exe" if sys.platform == "win32" else ""
    return resource_root() / "vendor" / (name + suffix)
