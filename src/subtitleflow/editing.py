"""Preserve exact previous bytes and roll back partial subtitle edits."""
import json
import shutil
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from .errors import AppError
from .storage import atomic_write_bytes
from .subtitles import Segment, render, validate


def save_edits(outputs: list[Path], segments: list[Segment]) -> Path:
    validate(segments)
    if not segments or not outputs:
        raise AppError("至少保留一行字幕，并选择此任务的有效输出文件。")
    outputs = [p.resolve() for p in outputs]
    first = outputs[0]
    if len(set(outputs)) != len(outputs) or any(
        p.parent != first.parent or p.stem != first.stem or p.suffix not in {".srt", ".vtt", ".txt"}
        for p in outputs
    ):
        raise AppError("字幕输出组无效，请从历史任务重新打开。")
    sidecar = first.with_suffix(".subtitleflow.json")
    targets = [*outputs, sidecar]
    if any(not p.is_file() for p in targets):
        raise AppError("字幕或编辑数据已移动、删除，请还原文件后重试。")
    original = {p: p.read_bytes() for p in targets}
    replacements = {p: render(segments, p.suffix[1:]).encode("utf-8") for p in outputs}
    replacements[sidecar] = json.dumps([asdict(s) for s in segments], ensure_ascii=False, indent=2).encode("utf-8")
    backup = first.parent / "字幕修改备份" / (
        first.stem + "_" + datetime.now().strftime("%Y%m%d-%H%M%S") + "_" + uuid.uuid4().hex[:8])
    backup.mkdir(parents=True, exist_ok=False)
    try:
        for path, content in original.items():
            atomic_write_bytes(backup / path.name, content)
    except Exception:
        shutil.rmtree(backup, ignore_errors=True)
        raise
    written: list[Path] = []
    try:
        for path, content in replacements.items():
            atomic_write_bytes(path, content)
            written.append(path)
    except Exception as exc:
        failures = []
        for path in reversed(written):
            try:
                atomic_write_bytes(path, original[path])
            except OSError:
                failures.append(path.name)
        if failures:
            raise AppError(f"保存失败，部分字幕无法自动还原：{'、'.join(failures)}。完整原文件在：{backup}") from exc
        raise AppError(f"保存失败，已还原此组字幕。请关闭占用文件的软件后重试。原文件备份：{backup}") from exc
    return backup
