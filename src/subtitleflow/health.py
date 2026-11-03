import shutil
import tempfile
import threading
from pathlib import Path
from .config import Settings
from .errors import explain
from .media import ensure_writable
from .models import ModelManager
from .paths import data_root
from .process import ProcessRunner


def check_environment(settings: Settings, models: ModelManager, cancel: threading.Event) -> list[tuple[str, bool, str]]:
    results = []
    runner = ProcessRunner()
    for name, arg in [("ffmpeg", "-version"), ("ffprobe", "-version"), ("whisper-cli", "-h")]:
        try:
            runner.run(settings.tool(name), [arg], cancel, timeout=20)
            results.append((name, True, "可用"))
        except Exception as exc:
            results.append((name, False, explain(exc)))
    for title, folder in [("输出目录", Path(settings.output_dir)), ("本地数据目录", data_root()),
                          ("临时目录", Path(tempfile.gettempdir()))]:
        try:
            ensure_writable(folder, 256 * 1024 * 1024)
            results.append((title, True, f"可写 · 剩余 {shutil.disk_usage(folder).free // (1024**2)} MB"))
        except Exception as exc:
            results.append((title, False, explain(exc)))
    for key in ("base", "small"):
        try:
            ready = models.ready(key, cancel)
            results.append((f"{key} 多语言模型", ready, "校验通过" if ready else "未准备，请前往模型管理下载 / 导入"))
        except Exception as exc:
            results.append((f"{key} 多语言模型", False, explain(exc)))
    return results
