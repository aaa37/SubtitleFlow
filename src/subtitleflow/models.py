import hashlib
import os
import shutil
import tempfile
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from .errors import AppError, Cancelled
from .paths import data_root
from . import __version__


@dataclass(frozen=True)
class ModelSpec:
    key: str
    title: str
    size: int
    sha256: str

    @property
    def url(self) -> str:
        return f"https://huggingface.co/ggerganov/whisper.cpp/resolve/5359861c739e955e79d9a303bcbc70fb988958b1/ggml-{self.key}.bin"


MODELS = {
    "base": ModelSpec("base", "速度优先 · base 多语言", 147951465,
                      "60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe"),
    "small": ModelSpec("small", "准确率优先 · small 多语言", 487601967,
                       "1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b"),
}


class ModelManager:
    def __init__(self, folder: Path | None = None) -> None:
        self.folder = folder or data_root() / "models"

    def path(self, key: str) -> Path:
        return self.folder / f"ggml-{MODELS[key].key}.bin"

    def verify_file(self, file: Path, spec: ModelSpec, cancel: threading.Event) -> bool:
        if not file.is_file() or file.stat().st_size != spec.size:
            return False
        sha = hashlib.sha256()
        with file.open("rb") as f:
            while chunk := f.read(1024 * 1024):
                if cancel.is_set():
                    raise Cancelled()
                sha.update(chunk)
        return sha.hexdigest() == spec.sha256

    def ready(self, key: str, cancel: threading.Event) -> bool:
        return self.verify_file(self.path(key), MODELS[key], cancel)

    def install(self, key: str, cancel: threading.Event, progress: Callable[[int, int], None],
                local: Path | None = None, opener: Callable = urllib.request.urlopen) -> Path:
        spec = MODELS[key]
        self.folder.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(self.folder).free < spec.size + 64 * 1024 * 1024:
            raise AppError("模型目录空间不足，请至少预留模型大小加 64 MB 的可用空间。")
        fd, temp = tempfile.mkstemp(prefix=f".{key}-", suffix=".part", dir=self.folder)
        os.close(fd)
        temporary = Path(temp)
        try:
            if cancel.is_set():
                raise Cancelled()
            if local is not None:
                stream = local.open("rb")
            else:
                request = urllib.request.Request(spec.url, headers={"User-Agent": f"SubtitleFlow/{__version__}"})
                stream = opener(request, timeout=20)
            received = 0
            sha = hashlib.sha256()
            with stream, temporary.open("wb") as target:
                while chunk := stream.read(256 * 1024):
                    if cancel.is_set():
                        raise Cancelled()
                    received += len(chunk)
                    if received > spec.size:
                        raise AppError("模型文件大小与官方清单不符，已拒绝安装。")
                    target.write(chunk)
                    sha.update(chunk)
                    progress(received, spec.size)
                target.flush()
                os.fsync(target.fileno())
            if cancel.is_set():
                raise Cancelled()
            if received != spec.size or sha.hexdigest() != spec.sha256:
                raise AppError("模型下载不完整或 SHA-256 校验失败，已清除临时文件。请点击下载重试，或导入官方模型。")
            os.replace(temporary, self.path(key))
            return self.path(key)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            raise AppError(f"模型下载失败：网络不可用或连接中断。请检查网络后重试，或导入官方模型。详情：{exc}") from exc
        finally:
            temporary.unlink(missing_ok=True)
