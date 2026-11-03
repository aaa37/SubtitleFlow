"""Provenance for tests of actual frozen artifacts."""
import hashlib
import platform
import sys
from pathlib import Path
from . import __version__
from PySide6.QtGui import QGuiApplication


def runtime_facts() -> dict[str, object]:
    with Path(sys.executable).open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    return {"platform": sys.platform, "machine": platform.machine(),
            "frozen": bool(getattr(sys, "frozen", False)), "version": __version__,
            "application_sha256": digest,
            "qt_platform": QGuiApplication.platformName() if QGuiApplication.instance() else None}
