import traceback
from collections.abc import Callable
from PySide6.QtCore import QObject, QThread, Signal, Slot
from ..errors import explain


class TaskThread(QThread):
    """Run finite work without a moved QObject or a second worker lifetime."""
    result = Signal(object)
    error = Signal(str)
    changed = Signal(object)
    progress = Signal(int, int)

    def __init__(self, work: Callable, parent: QObject) -> None:
        super().__init__(parent)
        self.work = work

    def run(self) -> None:
        try:
            self.result.emit(self.work(self))
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error(traceback.format_exc())
            self.error.emit(explain(exc))


class CallbackBridge(QObject):
    """Always invoke Python callbacks from this QObject's GUI-thread affinity."""
    def __init__(self, parent: QObject, result=None, changed=None, progress=None, error=None, finished=None) -> None:
        super().__init__(parent)
        self.result_callback = result
        self.changed_callback = changed
        self.progress_callback = progress
        self.error_callback = error
        self.finished_callback = finished

    @Slot(object)
    def on_result(self, value: object) -> None:
        if self.result_callback:
            self.result_callback(value)

    @Slot(object)
    def on_changed(self, value: object) -> None:
        if self.changed_callback:
            self.changed_callback(value)

    @Slot(int, int)
    def on_progress(self, current: int, total: int) -> None:
        if self.progress_callback:
            self.progress_callback(current, total)

    @Slot(str)
    def on_error(self, message: str) -> None:
        if self.error_callback:
            self.error_callback(message)

    @Slot()
    def on_finished(self) -> None:
        if self.finished_callback:
            self.finished_callback()
        self.deleteLater()
