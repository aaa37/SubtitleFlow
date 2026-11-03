import logging
import tempfile
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from .asr import WhisperAdapter
from .errors import AppError, Cancelled, explain
from .media import MediaAdapter, ensure_writable
from .models import ModelManager
from .storage import read_json, write_json
from .subtitles import Segment, export_new

log = logging.getLogger(__name__)


@dataclass
class Job:
    source: Path
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    state: str = "等待处理"
    duration: float = 0
    progress: float | None = None
    error: str = ""
    outputs: list[Path] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)


class HistoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def entries(self) -> list[dict]:
        data = read_json(self.path, [])
        return [x for x in data if isinstance(x, dict)] if isinstance(data, list) else []

    def append(self, job: Job) -> None:
        from datetime import datetime
        rows = self.entries()
        rows.insert(0, {"time": datetime.now().astimezone().isoformat(timespec="seconds"),
                       "source": str(job.source), "state": job.state, "error": job.error,
                       "outputs": [str(p) for p in job.outputs]})
        write_json(self.path, rows[:500])


class BatchEngine:
    def __init__(self, media: MediaAdapter, asr: WhisperAdapter, models: ModelManager,
                 history: HistoryStore | None = None) -> None:
        self.media, self.asr, self.models, self.history = media, asr, models, history
        self.cancel_current = threading.Event()
        self.stop_all = threading.Event()

    def stop(self) -> None:
        self.stop_all.set()
        self.cancel_current.set()

    def run(self, jobs: list[Job], output: Path, key: str, language: str, formats: list[str],
            update: Callable[[Job], None], overall: Callable[[int, int], None]) -> None:
        # Events are reset by the controller before starting, never here (avoid lost early cancellation).
        for index, job in enumerate(jobs):
            if self.stop_all.is_set():
                break
            try:
                self._one(job, output, key, language, formats, update)
                job.state, job.progress = "已完成", 100
            except Cancelled:
                job.state, job.progress = "已取消", None
            except Exception as exc:
                job.state, job.progress, job.error = "失败", None, explain(exc)
                log.exception("job failed: %s", job.source.name)
            finally:
                update(job)
                if self.history:
                    try:
                        self.history.append(job)
                    except Exception:
                        log.exception("history could not be saved")
                overall(index + 1, len(jobs))
                self.cancel_current.clear()
        if self.stop_all.is_set():
            for job in jobs:
                if job.state == "等待处理":
                    job.state = "已取消"
                    update(job)
                    if self.history:
                        try:
                            self.history.append(job)
                        except Exception:
                            log.exception("cancelled history could not be saved")
            overall(len(jobs), len(jobs))

    def _one(self, job: Job, output: Path, key: str, language: str, formats: list[str],
             update: Callable[[Job], None]) -> None:
        job.error = ""
        job.state, job.progress = "检查文件与模型", None
        update(job)
        if not self.models.ready(key, self.cancel_current):
            raise AppError("模型缺失或校验失败，请在「模型管理」下载或重新导入。")
        ensure_writable(output)
        info = self.media.probe(job.source, self.cancel_current)
        job.duration = info.duration
        # Use private OS temp directory, removed even on cancellation or failure.
        with tempfile.TemporaryDirectory(prefix="subtitleflow-") as temporary:
            folder = Path(temporary)
            ensure_writable(folder, int(info.duration * 32000) + 64 * 1024 * 1024)
            wav = folder / "audio.wav"
            job.state, job.progress = "提取音频", 0
            update(job)

            def progress(value: float) -> None:
                job.progress = value
                update(job)

            self.media.extract(job.source, wav, info, self.cancel_current, progress)
            job.state, job.progress = "正在识别（本地 CPU）", None
            update(job)
            segments = self.asr.transcribe(wav, self.models.path(key), language, self.cancel_current)
            if self.cancel_current.is_set():
                raise Cancelled()
            if any(s.start >= info.duration or s.end > info.duration + 1 for s in segments):
                raise AppError("识别时间超出媒体时长，结果可能包含幻觉文本。请检查音频或换用 small 模型重试。")
            segments = [Segment(s.start, min(s.end, info.duration), s.text) for s in segments]
            job.state, job.progress = "保存字幕", None
            update(job)
            job.outputs = export_new(output, job.source.stem, segments, formats)
            job.segments = segments
