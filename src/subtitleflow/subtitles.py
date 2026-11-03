import json
import math
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from .errors import AppError
from .storage import atomic_write


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str


def validate(segments: Iterable[Segment]) -> list[Segment]:
    result = list(segments)
    previous = 0.0
    for index, s in enumerate(result, 1):
        if (not math.isfinite(s.start) or not math.isfinite(s.end) or s.start < previous or
                s.start < 0 or round(s.end * 1000) <= round(s.start * 1000)):
            raise AppError(f"第 {index} 行时间无效：开始时间需按顺序排列，结束时间必须晚于开始时间。")
        if not s.text.strip():
            raise AppError(f"第 {index} 行字幕为空。请填写文本或删除此行。")
        previous = s.start
    return result


def timestamp(seconds: float, separator: str = ",") -> str:
    if not math.isfinite(seconds) or seconds < 0:
        raise AppError("时间戳必须为非负数。")
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"


def parse_timestamp(text: str) -> float:
    match = re.fullmatch(r"(\d{2,}):([0-5]\d):([0-5]\d)[,.](\d{3})", text.strip())
    if not match:
        raise AppError("时间格式应为 00:00:01,500（时:分:秒,毫秒）。")
    h, m, s, ms = map(int, match.groups())
    return h * 3600 + m * 60 + s + ms / 1000


def render(segments: list[Segment], fmt: str) -> str:
    validate(segments)
    if fmt == "txt":
        return "\n".join(s.text.strip() for s in segments) + "\n"
    if fmt not in {"srt", "vtt"}:
        raise AppError("不支持的字幕格式。")
    sep = "," if fmt == "srt" else "."
    blocks = []
    for i, s in enumerate(segments, 1):
        # Avoid accidentally creating a new cue from blank lines in edited text.
        text = "\n".join(line for line in s.text.strip().splitlines() if line.strip())
        if fmt == "vtt":
            text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        blocks.append(f"{i}\n{timestamp(s.start, sep)} --> {timestamp(s.end, sep)}\n{text}\n")
    return ("WEBVTT\n\n" if fmt == "vtt" else "") + "\n".join(blocks)


def safe_stem(name: str) -> str:
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")[:90] or "字幕"
    if stem.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                                        *(f"LPT{i}" for i in range(1, 10))}:
        stem = "_" + stem
    return stem


def export_new(folder: Path, stem: str, segments: list[Segment], formats: list[str]) -> list[Path]:
    """Reserve every target exclusively; rollback only files owned by this call."""
    if not formats or set(formats) - {"srt", "vtt", "txt"}:
        raise AppError("请至少选择一种有效的导出格式。")
    validate(segments)
    formats = list(dict.fromkeys(formats))
    folder.mkdir(parents=True, exist_ok=True)
    for number in range(10000):
        base = safe_stem(stem) + (f" ({number})" if number else "")
        outputs = [folder / f"{base}.{fmt}" for fmt in formats]
        sidecar = folder / f"{base}.subtitleflow.json"
        owned: list[Path] = []
        try:
            for path in [*outputs, sidecar]:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
                owned.append(path)
        except FileExistsError:
            for path in owned:
                path.unlink(missing_ok=True)
            continue
        except Exception:
            for path in owned:
                path.unlink(missing_ok=True)
            raise
        try:
            for path, fmt in zip(outputs, formats):
                atomic_write(path, render(segments, fmt))
            atomic_write(sidecar, json.dumps([asdict(s) for s in segments], ensure_ascii=False, indent=2))
            return outputs
        except Exception:
            for path in owned:
                path.unlink(missing_ok=True)
            raise
    raise AppError("同名输出文件过多，请更换输出目录。")
