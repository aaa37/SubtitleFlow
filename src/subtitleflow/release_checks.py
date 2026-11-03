"""Release evidence checks; checkboxes alone do not certify a Windows build."""
import hashlib
import json
import struct
from pathlib import Path
from . import __version__
from .errors import AppError

QT_MODULES = {"core", "gui", "widgets", "svg", "svgwidgets", "dbus"}


def sha256(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def require_x64_pe(executable: Path) -> None:
    try:
        with executable.open("rb") as file:
            if file.read(2) != b"MZ":
                raise ValueError("not PE")
            file.seek(0x3C)
            offset = struct.unpack("<I", file.read(4))[0]
            file.seek(offset)
            if file.read(4) != b"PE\0\0" or struct.unpack("<H", file.read(2))[0] != 0x8664:
                raise ValueError("not x64")
    except (OSError, ValueError, struct.error) as exc:
        raise AppError("发行程序不是有效 Windows x64 PE 文件。") from exc


def verify_frozen_evidence(path: Path, executable: Path, *, asr: bool = False) -> None:
    try:
        evidence = json.loads(path.read_text(encoding="utf-8-sig"))
        runtime = evidence["runtime"]
        if (runtime["platform"] != "win32" or runtime.get("qt_platform") != "windows" or not runtime["frozen"] or
                runtime["version"] != __version__ or runtime["application_sha256"] != sha256(executable)):
            raise ValueError("not the current frozen Windows executable")
        if asr:
            if evidence.get("state") != "已完成" or not evidence.get("transcript"):
                raise ValueError("no actual ASR result")
        elif evidence.get("gui") != "ok" or not evidence.get("docs") or not evidence.get("icon"):
            raise ValueError("missing GUI resources")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise AppError(f"发行证据不足或与当前 EXE 不匹配：{path.name}。请用最终 Windows 成品重新测试。") from exc


def audit_qt_modules(bundle: Path) -> list[str]:
    observed = []
    for path in bundle.rglob("*"):
        name = path.name.lower()
        if path.is_file() and name.startswith("qt6") and name.endswith(".dll"):
            if name[3:-4] not in QT_MODULES:
                raise AppError(f"发现未审查 Qt 模块 {path.name}，先补齐对应源码与许可证再发行。")
            observed.append(path.name)
    if not {"qt6core.dll", "qt6gui.dll", "qt6widgets.dll"}.issubset({x.lower() for x in observed}):
        raise AppError("Qt 核心运行库不完整。")
    return sorted(set(observed))
