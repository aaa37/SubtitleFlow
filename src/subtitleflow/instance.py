"""One desktop process per data directory, including stale-PID recovery."""
from pathlib import Path
from PySide6.QtCore import QLockFile
from .errors import AppError


def acquire_instance(folder: Path) -> QLockFile:
    folder.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(folder / "application.lock"))
    lock.setStaleLockTime(30000)
    if not lock.tryLock(0):
        raise AppError("字幕工坊已经在运行，请切换到已打开的窗口。若程序意外退出，请稍候再试。")
    return lock
