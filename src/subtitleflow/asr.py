import json
import os
import threading
from pathlib import Path
from .errors import AppError, Cancelled
from .process import ProcessRunner
from .subtitles import Segment, validate


class WhisperAdapter:
    def __init__(self, executable: Path, runner: ProcessRunner | None = None) -> None:
        self.executable = executable
        self.runner = runner or ProcessRunner()

    def transcribe(self, wav: Path, model: Path, language: str, cancel: threading.Event) -> list[Segment]:
        if not model.is_file():
            raise AppError("模型尚未准备好，请前往「模型管理」下载或导入 base / small 多语言模型。")
        if language not in {"zh", "en", "auto"}:
            raise AppError("不支持的识别语言。")
        output = wav.parent / "recognition"
        self.runner.run(self.executable, ["-m", str(model), "-f", str(wav), "-l", language, "-oj",
                        "-of", str(output), "-t", str(max(1, min(8, (os.cpu_count() or 2) - 1))), "-np"], cancel)
        if cancel.is_set():
            raise Cancelled()
        try:
            data = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
            result = [Segment(float(s["offsets"]["from"]) / 1000,
                              float(s["offsets"]["to"]) / 1000, s["text"].strip())
                      for s in data["transcription"] if s["text"].strip()]
            validate(result)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise AppError("识别引擎返回了无法解析的字幕，请重新安装匹配版本的 whisper.cpp。") from exc
        if not result:
            raise AppError("未识别到有效语音。请确认音量、语言设置及文件内容。")
        return result
