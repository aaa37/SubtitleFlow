import json
import math
import shutil
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable
from .errors import AppError, Cancelled
from .process import ProcessRunner

EXTENSIONS = {".mp4", ".mov", ".mkv", ".mp3", ".wav", ".m4a"}


def discover(paths: Iterable[Path]) -> list[Path]:
    result: dict[str, Path] = {}
    for path in paths:
        candidates = sorted(path.rglob("*")) if path.is_dir() else [path]
        for candidate in candidates:
            if candidate.is_file() and candidate.suffix.lower() in EXTENSIONS:
                resolved = candidate.resolve()
                result[str(resolved).casefold() if __import__("os").name == "nt" else str(resolved)] = resolved
    return list(result.values())


@dataclass(frozen=True)
class MediaInfo:
    duration: float
    audio: bool


def ensure_writable(folder: Path, required: int = 32 * 1024 * 1024) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=folder) as f:
        f.write(b"ok")
        f.flush()
    if shutil.disk_usage(folder).free < required:
        raise AppError("磁盘剩余空间不足。请清理磁盘或选择其他输出目录。")


class MediaAdapter:
    def __init__(self, ffmpeg: Path, ffprobe: Path, runner: ProcessRunner | None = None) -> None:
        self.ffmpeg, self.ffprobe = ffmpeg, ffprobe
        self.runner = runner or ProcessRunner()

    def probe(self, source: Path, cancel: threading.Event) -> MediaInfo:
        if not source.is_file() or source.stat().st_size == 0:
            raise AppError("文件不存在或为空，请重新选择有效音视频文件。")
        raw = self.runner.run(self.ffprobe, ["-v", "error", "-show_format", "-show_streams", "-of", "json",
                                                 str(source)], cancel, timeout=60)
        try:
            data = json.loads(raw)
            streams = data.get("streams", [])
            durations = [float(s["duration"]) for s in streams if s.get("duration") not in (None, "N/A")]
            duration = float(data.get("format", {}).get("duration", max(durations, default=0)))
        except (ValueError, TypeError, KeyError) as exc:
            raise AppError("无法读取文件时长。请检查文件是否完整。") from exc
        if not math.isfinite(duration) or duration <= 0:
            raise AppError("文件时长无效，无法处理直播流或损坏文件。")
        return MediaInfo(duration, any(s.get("codec_type") == "audio" for s in streams))

    def extract(self, source: Path, target: Path, info: MediaInfo, cancel: threading.Event,
                progress: Callable[[float], None]) -> None:
        if not info.audio:
            raise AppError("此视频没有音轨，无法生成语音字幕。请选择带声音的视频。")

        def line(value: str) -> None:
            if value.startswith("out_time_us="):
                try:
                    progress(min(100, max(0, int(value.split("=", 1)[1]) / 1_000_000 / info.duration * 100)))
                except ValueError:
                    pass

        self.runner.run(self.ffmpeg, ["-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i",
                         str(source), "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000", "-c:a",
                         "pcm_s16le", "-progress", "pipe:1", str(target)], cancel, line)
        if cancel.is_set():
            raise Cancelled()
        if not target.is_file() or target.stat().st_size <= 44:
            raise AppError("音频提取结果为空，请检查文件的音轨。")
        # Packet timestamps may end before the final sample. Only mark complete
        # after the process succeeds and its actual output has been validated.
        progress(100)
