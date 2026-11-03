"""Cancellation-safe subprocess boundary; never invokes a user-constructed shell."""
import logging
import os
import queue
import signal
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from typing import Callable
from .errors import AppError, Cancelled

log = logging.getLogger(__name__)


class ProcessRunner:
    def run(self, executable: Path, args: list[str], cancel: threading.Event,
            on_line: Callable[[str], None] | None = None, timeout: float = 86400) -> str:
        if cancel.is_set():
            raise Cancelled()
        executable = executable.resolve()
        if not executable.is_file():
            raise AppError(f"缺少组件：{executable.name}。请在「设置」中重新选择官方组件文件夹，或重新解压完整软件包。")
        kwargs: dict = {"start_new_session": True} if os.name != "nt" else {
            "creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
        try:
            proc = subprocess.Popen([str(executable), *args], stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, **kwargs)
        except OSError as exc:
            raise AppError(f"无法启动 {executable.name}。请确认组件适用于 Windows x64，重新解压软件包。{exc}") from exc
        lines: queue.Queue[str | None] = queue.Queue(maxsize=4096)
        done = threading.Event()

        def read() -> None:
            assert proc.stdout is not None
            try:
                for raw in iter(proc.stdout.readline, b""):
                    value = raw.decode("utf-8", errors="replace").rstrip()
                    while not done.is_set():
                        try:
                            lines.put(value, timeout=0.1)
                            break
                        except queue.Full:
                            pass
            finally:
                proc.stdout.close()
                while not done.is_set():
                    try:
                        lines.put(None, timeout=0.1)
                        break
                    except queue.Full:
                        pass

        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        tail: deque[str] = deque(maxlen=512)
        started = time.monotonic()
        try:
            while True:
                if cancel.is_set():
                    raise Cancelled()
                if time.monotonic() - started > timeout:
                    raise AppError(f"{executable.name} 响应超时。请重试，或检查输入文件。")
                try:
                    line = lines.get(timeout=0.05)
                except queue.Empty:
                    continue
                if line is None:
                    break
                tail.append(line)
                if on_line:
                    on_line(line)
            code = proc.wait(timeout=5)
            output = "\n".join(tail)
            if code:
                log.error("%s exited %s: %s", executable.name, code, output[-4000:])
                raise AppError(f"{executable.name} 异常退出（{code}）。文件可能损坏、编码不支持或内存不足。"
                               f"\n诊断：{output[-1000:]}")
            return output
        finally:
            done.set()
            if proc.poll() is None:
                if os.name == "nt":
                    subprocess.run([str(Path(os.environ.get("SystemRoot", "C:/Windows")) /
                                        "System32/taskkill.exe"), "/PID", str(proc.pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=subprocess.CREATE_NO_WINDOW, timeout=10, check=False)
                else:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                proc.kill()
                proc.wait(timeout=10)
            reader.join(timeout=2)
