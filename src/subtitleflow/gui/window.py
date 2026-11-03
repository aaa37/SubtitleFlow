import copy
import threading
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QCheckBox, QLineEdit,
    QFileDialog, QMessageBox, QProgressBar, QGroupBox, QTextBrowser, QAbstractItemView)
from .. import __version__
from ..asr import WhisperAdapter
from ..config import Settings
from ..errors import AppError, explain
from ..health import check_environment
from ..jobs import BatchEngine, HistoryStore, Job
from ..media import MediaAdapter, discover
from ..models import MODELS, ModelManager
from ..paths import data_root, resource_root
from ..storage import read_json
from ..subtitles import Segment
from .editor import SubtitleEditor
from .style import STYLE
from .workers import TaskThread, CallbackBridge


class DropLabel(QLabel):
    dropped = Signal(object)

    def __init__(self) -> None:
        super().__init__("拖入音视频或文件夹，开始批量生成字幕\nMP4 · MOV · MKV · MP3 · WAV · M4A")
        self.setObjectName("drop")
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        self.dropped.emit([Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile()])
        event.acceptProposedAction()


def button(text, callback, primary=False) -> QPushButton:
    widget = QPushButton(text)
    if primary:
        widget.setObjectName("primary")
    widget.clicked.connect(callback)
    return widget


def table(headers) -> QTableWidget:
    widget = QTableWidget(0, len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.setAlternatingRowColors(True)
    widget.setSelectionBehavior(QAbstractItemView.SelectRows)
    widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
    widget.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
    widget.horizontalHeader().setStretchLastSection(True)
    widget.verticalHeader().setVisible(False)
    return widget


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings | None = None, startup_check: bool = True) -> None:
        super().__init__()
        self.settings = settings or Settings.load()
        self.models = ModelManager()
        self.history = HistoryStore(data_root() / "history.json")
        self.jobs: list[Job] = []
        self.engine: BatchEngine | None = None
        self.threads: dict[str, tuple[TaskThread, CallbackBridge]] = {}
        self.model_cancel = threading.Event()
        self.health_cancel = threading.Event()
        self.import_cancel = threading.Event()
        self.closing = False
        self.error_dialogs: list[QMessageBox] = []
        self.setWindowTitle(f"字幕工坊 SubtitleFlow · {__version__}")
        self.setWindowIcon(QIcon(str(resource_root() / "assets/icon.svg")))
        self.resize(1260, 840)
        self.setMinimumSize(960, 700)
        self.setStyleSheet(STYLE)
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(190)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(16, 28, 16, 24)
        brand = QLabel("字幕工坊")
        brand.setStyleSheet("font-size: 18pt; font-weight: 600; padding: 8px 0 26px 0")
        nav.addWidget(brand)
        subtitle = QLabel("SubtitleFlow")
        subtitle.setStyleSheet("font-size: 12pt; padding-bottom: 22px")
        nav.addWidget(subtitle)
        self.stack = QStackedWidget()
        self.nav_buttons = []
        for index, label in enumerate(["批量字幕", "历史任务", "模型管理", "设置", "使用帮助"]):
            b = button(label, lambda checked=False, i=index: self.navigate(i))
            b.setCheckable(True)
            nav.addWidget(b)
            self.nav_buttons.append(b)
        nav.addStretch()
        nav.addWidget(QLabel(f"本地处理 · 无需账号\nv{__version__}  基础版"))
        root.addWidget(sidebar)
        root.addWidget(self.stack, 1)
        self.build_batch()
        self.build_history()
        self.build_models()
        self.build_settings()
        self.build_help()
        self.navigate(0)
        if startup_check:
            QTimer.singleShot(100, self.run_health)

    def page(self, title, subtitle) -> QVBoxLayout:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 26, 30, 24)
        layout.setSpacing(14)
        heading = QLabel(title)
        heading.setObjectName("title")
        layout.addWidget(heading)
        caption = QLabel(subtitle)
        caption.setObjectName("muted")
        caption.setWordWrap(True)
        layout.addWidget(caption)
        self.stack.addWidget(page)
        return layout

    def navigate(self, index) -> None:
        self.stack.setCurrentIndex(index)
        for i, b in enumerate(self.nav_buttons):
            b.setChecked(i == index)
        if index == 1:
            self.load_history()

    def launch(self, key, work, result=None, changed=None, progress=None, finished=None) -> None:
        if key in self.threads:
            return
        thread = TaskThread(work, self)

        def on_finished() -> None:
            # finished() precedes native TLS cleanup; join before releasing any
            # references or allowing the window to be destroyed.
            thread.wait()
            self.threads.pop(key, None)
            try:
                if finished:
                    finished()
            finally:
                thread.deleteLater()

        bridge = CallbackBridge(self, result=result, changed=changed, progress=progress,
                                error=self.show_error, finished=on_finished)
        thread.result.connect(bridge.on_result, Qt.QueuedConnection)
        thread.changed.connect(bridge.on_changed, Qt.QueuedConnection)
        thread.progress.connect(bridge.on_progress, Qt.QueuedConnection)
        thread.error.connect(bridge.on_error, Qt.QueuedConnection)
        thread.finished.connect(bridge.on_finished, Qt.QueuedConnection)
        self.threads[key] = (thread, bridge)
        thread.start()

    @Slot(str)
    def show_error(self, message) -> None:
        if self.closing:
            return
        # Never enter a nested modal event loop from a task's queued callback:
        # its completion may otherwise delete the callback receiver mid-call.
        dialog = QMessageBox(QMessageBox.Warning, "需要处理", str(message), QMessageBox.Ok, self)
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        self.error_dialogs.append(dialog)
        dialog.finished.connect(lambda _code, item=dialog: self.dismiss_error(item))
        dialog.open()

    def dismiss_error(self, dialog: QMessageBox) -> None:
        if dialog in self.error_dialogs:
            self.error_dialogs.remove(dialog)

    def build_batch(self) -> None:
        layout = self.page("批量生成字幕", "选择文件、准备模型，然后一键生成。音视频留在你的电脑里。")
        self.drop = DropLabel()
        self.drop.dropped.connect(self.import_paths)
        layout.addWidget(self.drop)
        row = QHBoxLayout()
        self.add_button = button("＋ 添加文件", self.choose_files)
        self.folder_button = button("添加文件夹", self.choose_folder)
        self.clear_button = button("清空列表", self.clear_jobs)
        row.addWidget(self.add_button)
        row.addWidget(self.folder_button)
        row.addWidget(self.clear_button)
        row.addStretch()
        row.addWidget(button("编辑所选字幕", self.edit_selected))
        row.addWidget(button("查看失败原因", self.failure_detail))
        layout.addLayout(row)
        self.queue_table = table(["文件名", "时长", "状态 / 阶段进度", "输出位置"])
        self.queue_table.setColumnWidth(0, 230)
        self.queue_table.setColumnWidth(1, 85)
        self.queue_table.setColumnWidth(2, 200)
        self.queue_table.doubleClicked.connect(self.edit_selected)
        layout.addWidget(self.queue_table, 1)
        group = QGroupBox("生成设置")
        form = QVBoxLayout(group)
        options = QHBoxLayout()
        self.language = QComboBox()
        for title, key in [("中文", "zh"), ("英文", "en"), ("自动检测", "auto")]:
            self.language.addItem(title, key)
        self.language.setCurrentIndex(max(0, self.language.findData(self.settings.language)))
        self.model_choice = QComboBox()
        for key, spec in MODELS.items():
            self.model_choice.addItem(spec.title, key)
        self.model_choice.setCurrentIndex(max(0, self.model_choice.findData(self.settings.model)))
        options.addWidget(QLabel("识别语言"))
        options.addWidget(self.language)
        options.addWidget(QLabel("模型"))
        options.addWidget(self.model_choice, 1)
        self.format_checks = {}
        for fmt in ["srt", "vtt", "txt"]:
            check = QCheckBox(fmt.upper())
            check.setChecked(fmt == "srt")
            self.format_checks[fmt] = check
            options.addWidget(check)
        form.addLayout(options)
        output = QHBoxLayout()
        output.addWidget(QLabel("输出到"))
        self.output = QLineEdit(self.settings.output_dir)
        output.addWidget(self.output, 1)
        self.output_button = button("选择目录", self.choose_output)
        output.addWidget(self.output_button)
        output.addWidget(button("打开目录", self.open_output))
        form.addLayout(output)
        layout.addWidget(group)
        self.status = QLabel("就绪 · 添加文件后即可开始；首次使用请先准备模型。")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        bottom = QHBoxLayout()
        self.total_progress = QProgressBar()
        self.total_progress.setRange(0, 1)
        self.total_progress.setValue(0)
        self.total_progress.setFormat("已结束任务 %v / %m")
        bottom.addWidget(self.total_progress, 1)
        self.cancel_button = button("取消当前", self.cancel_current)
        self.cancel_button.setEnabled(False)
        self.stop_button = button("停止全部", self.stop_all)
        self.stop_button.setEnabled(False)
        self.start_button = button("开始生成", self.start_batch, True)
        bottom.addWidget(self.cancel_button)
        bottom.addWidget(self.stop_button)
        bottom.addWidget(self.start_button)
        layout.addLayout(bottom)

    def refresh_start_enabled(self) -> None:
        self.start_button.setEnabled(not any(k in self.threads for k in ("batch", "import", "model")))

    def choose_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "选择音视频文件", "",
            "音视频 (*.mp4 *.mov *.mkv *.mp3 *.wav *.m4a);;所有文件 (*)")
        self.import_paths([Path(p) for p in files])

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹（包含子文件夹）")
        if folder:
            self.import_paths([Path(folder)])

    def import_paths(self, paths: list[Path]) -> None:
        if not paths or "batch" in self.threads or "import" in self.threads:
            return
        self.import_cancel.clear()
        self.start_button.setEnabled(False)
        self.status.setText("正在查找文件并读取时长…")
        settings = copy.deepcopy(self.settings)

        def work(worker) -> list[Job]:
            media = MediaAdapter(settings.tool("ffmpeg"), settings.tool("ffprobe"))
            found = []
            for path in discover(paths):
                if self.import_cancel.is_set():
                    break
                job = Job(path)
                try:
                    job.duration = media.probe(path, self.import_cancel).duration
                except Exception as exc:
                    # Retain the file so the queue can report failures and recover after component repair.
                    job.error = explain(exc)
                found.append(job)
            return found

        self.launch("import", work, result=self.imported,
                    finished=self.refresh_start_enabled)

    @Slot(object)
    def imported(self, jobs) -> None:
        existing = {j.source for j in self.jobs}
        count = 0
        for job in jobs:
            if job.source not in existing:
                existing.add(job.source)
                self.jobs.append(job)
                count += 1
        self.refresh_jobs()
        self.status.setText(f"已添加 {count} 个文件，共 {len(self.jobs)} 个。文件夹会递归导入支持的格式。")

    def clear_jobs(self) -> None:
        if any(k in self.threads for k in ("batch", "import")):
            return
        self.jobs.clear()
        self.refresh_jobs()

    def refresh_jobs(self) -> None:
        self.queue_table.setRowCount(len(self.jobs))
        for row, job in enumerate(self.jobs):
            state = job.state + (f" · {job.progress:.0f}%" if job.progress is not None else "")
            duration = f"{int(job.duration)//60}:{int(job.duration)%60:02d}" if job.duration else "待检查"
            for column, text in enumerate([job.source.name, duration, state,
                                           str(job.outputs[0]) if job.outputs else "—"]):
                item = QTableWidgetItem(text)
                item.setToolTip(str(job.source) if column == 0 else job.error or text)
                self.queue_table.setItem(row, column, item)

    def choose_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择字幕保存目录", self.output.text())
        if folder:
            self.output.setText(folder)

    def open_output(self) -> None:
        folder = Path(self.output.text()).expanduser()
        if folder.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder.resolve())))
        else:
            self.show_error("输出目录尚不存在。请选择目录，或完成一次生成。")

    def start_batch(self) -> None:
        if any(k in self.threads for k in ("batch", "import", "model")):
            self.show_error("后台任务仍在进行，请等待当前操作完成。")
            return
        pending = [j for j in self.jobs if j.state != "已完成"]
        formats = [fmt for fmt, check in self.format_checks.items() if check.isChecked()]
        if not pending:
            self.show_error("请添加待处理音视频。已完成文件可在历史任务中打开。")
            return
        if not formats or not self.output.text().strip():
            self.show_error("请至少选择一种导出格式并选择输出目录。")
            return
        if "model" in self.threads:
            self.show_error("模型正在准备，请等待下载和校验结束。")
            return
        self.settings.output_dir = self.output.text().strip()
        self.settings.model = self.model_choice.currentData()
        self.settings.language = self.language.currentData()
        try:
            self.settings.save()
        except Exception as exc:
            self.show_error(explain(exc))
            return
        for job in pending:
            job.state = "等待处理"
            job.progress = None
        self.engine = BatchEngine(MediaAdapter(self.settings.tool("ffmpeg"), self.settings.tool("ffprobe")),
            WhisperAdapter(self.settings.tool("whisper-cli")), self.models, self.history)
        engine = self.engine
        key, language, folder = self.settings.model, self.settings.language, Path(self.settings.output_dir)
        self.set_busy(True)
        self.total_progress.setRange(0, len(pending))
        self.total_progress.setValue(0)
        self.status.setText("正在检查文件与模型；每个任务独立处理，失败后继续下一项。")
        self.launch("batch", lambda worker: engine.run(pending, folder, key, language, formats,
                    lambda j: worker.changed.emit(copy.deepcopy(j)), worker.progress.emit),
                    changed=self.job_changed, progress=self.batch_progress, finished=self.batch_done)

    def set_busy(self, busy) -> None:
        for widget in [self.start_button, self.add_button, self.folder_button, self.clear_button,
                       self.language, self.model_choice, self.output, self.output_button]:
            widget.setEnabled(not busy)
        for widget in self.format_checks.values():
            widget.setEnabled(not busy)
        self.drop.setAcceptDrops(not busy)
        self.cancel_button.setEnabled(busy)
        self.stop_button.setEnabled(busy)
        self.component_button.setEnabled(not busy)
        for b in self.model_buttons:
            b.setEnabled(not busy)

    @Slot(object)
    def job_changed(self, updated: Job) -> None:
        for index, job in enumerate(self.jobs):
            if job.id == updated.id:
                self.jobs[index] = updated
                break
        self.refresh_jobs()
        self.status.setText(f"{updated.source.name} · {updated.state}" +
                            (f"\n{updated.error}" if updated.error else ""))

    @Slot(int, int)
    def batch_progress(self, done: int, total: int) -> None:
        self.total_progress.setRange(0, total)
        self.total_progress.setValue(done)

    def batch_done(self) -> None:
        self.set_busy(False)
        ok = sum(j.state == "已完成" for j in self.jobs)
        failed = sum(j.state == "失败" for j in self.jobs)
        cancelled = sum(j.state == "已取消" for j in self.jobs)
        self.status.setText(f"处理结束：成功 {ok} · 失败 {failed} · 取消 {cancelled}。可编辑字幕或打开输出目录。")
        self.load_history()

    def cancel_current(self) -> None:
        if self.engine:
            self.engine.cancel_current.set()
            self.status.setText("正在取消当前任务并清理临时文件，随后继续下一项…")

    def stop_all(self) -> None:
        if self.engine:
            self.engine.stop()
            self.status.setText("正在停止队列并清理临时文件…")

    def failure_detail(self) -> None:
        row = self.queue_table.currentRow()
        if 0 <= row < len(self.jobs):
            self.show_error(self.jobs[row].error or "此文件尚无失败信息。")

    def edit_selected(self, *_) -> None:
        row = self.queue_table.currentRow()
        if 0 <= row < len(self.jobs) and self.jobs[row].outputs:
            self.open_editor(self.jobs[row].outputs)
        else:
            self.show_error("请先选中一个已完成的任务。")

    def open_editor(self, outputs) -> None:
        try:
            outputs = [Path(p) for p in outputs]
            if not outputs:
                raise AppError("此任务没有生成字幕。")
            segments = [Segment(**s) for s in read_json(outputs[0].with_suffix(".subtitleflow.json"), [])]
            if not segments:
                raise AppError("字幕编辑数据缺失。请保留字幕旁的 .subtitleflow.json 文件。")
            SubtitleEditor(segments, outputs, self).exec()
        except Exception as exc:
            self.show_error(explain(exc))

    def build_history(self) -> None:
        layout = self.page("历史任务", "记录保存在本机，最多保留最近 500 项。双击成功记录可编辑字幕。")
        self.history_table = table(["时间", "文件", "状态", "输出 / 原因"])
        self.history_table.setColumnWidth(0, 210)
        self.history_table.setColumnWidth(1, 210)
        self.history_table.doubleClicked.connect(self.edit_history)
        layout.addWidget(self.history_table)
        row = QHBoxLayout()
        row.addWidget(button("刷新记录", self.load_history))
        row.addWidget(button("打开所选输出目录", self.open_history_folder))
        row.addStretch()
        layout.addLayout(row)

    def load_history(self) -> None:
        self.history_rows = self.history.entries()
        self.history_table.setRowCount(len(self.history_rows))
        for row, entry in enumerate(self.history_rows):
            outputs = entry.get("outputs", [])
            values = [entry.get("time", ""), Path(entry.get("source", "")).name, entry.get("state", ""),
                      outputs[0] if outputs else entry.get("error", "")]
            for c, text in enumerate(values):
                item = QTableWidgetItem(str(text))
                item.setToolTip(str(text))
                self.history_table.setItem(row, c, item)

    def edit_history(self, *_) -> None:
        r = self.history_table.currentRow()
        if 0 <= r < len(self.history_rows):
            self.open_editor(self.history_rows[r].get("outputs", []))

    def open_history_folder(self) -> None:
        r = self.history_table.currentRow()
        if 0 <= r < len(self.history_rows):
            outputs = self.history_rows[r].get("outputs", [])
            if outputs:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(outputs[0]).parent)))

    def build_models(self) -> None:
        layout = self.page("模型管理", "只需准备一次，之后可离线转写。官方多语言权重；首次联网下载，支持导入官方模型。")
        self.model_buttons = []
        self.model_labels = {}
        for key, spec in MODELS.items():
            group = QGroupBox(spec.title)
            content = QVBoxLayout(group)
            desc = QLabel(f"文件大小 {spec.size / 1024**2:.1f} MB · 支持中文 / 英文\n"
                          + ("CPU 处理更轻量，建议先尝试。" if key == "base" else "占用更多内存，处理通常更慢。"))
            content.addWidget(desc)
            state = QLabel("尚未检查；点击检查环境验证模型完整性。")
            state.setWordWrap(True)
            self.model_labels[key] = state
            content.addWidget(state)
            row = QHBoxLayout()
            for title, callback in [("下载 / 重试", lambda checked=False, k=key: self.prepare_model(k)),
                                    ("导入本地模型", lambda checked=False, k=key: self.import_model(k)),
                                    ("官方模型页面", lambda checked=False: QDesktopServices.openUrl(
                                        QUrl("https://huggingface.co/ggerganov/whisper.cpp")))]:
                b = button(title, callback)
                row.addWidget(b)
                self.model_buttons.append(b)
            row.addStretch()
            content.addLayout(row)
            layout.addWidget(group)
        self.model_progress = QProgressBar()
        self.model_progress.setRange(0, 100)
        self.model_progress.setValue(0)
        layout.addWidget(self.model_progress)
        self.model_status = QLabel("采用临时下载、SHA-256 完整校验、原子安装；中断后重新下载。")
        self.model_status.setWordWrap(True)
        layout.addWidget(self.model_status)
        self.model_stop_button = button("取消模型准备", self.model_cancel.set)
        self.model_stop_button.setEnabled(False)
        layout.addWidget(self.model_stop_button)
        layout.addStretch()

    def import_model(self, key) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择官方 ggml 模型", "", "GGML 模型 (*.bin)")
        if path:
            self.prepare_model(key, Path(path))

    def prepare_model(self, key, local=None) -> None:
        if "model" in self.threads or "batch" in self.threads:
            return
        self.active_model_key = key
        self.model_cancel.clear()
        self.model_stop_button.setEnabled(True)
        for b in self.model_buttons:
            b.setEnabled(False)
        self.start_button.setEnabled(False)
        self.model_progress.setValue(0)
        self.model_status.setText(f"正在准备 {key} 模型，请保持软件开启…")
        self.launch("model", lambda worker: self.models.install(key, self.model_cancel, worker.progress.emit, local),
                    result=self.model_installed, progress=self.model_download_progress,
                    finished=self.model_finished)

    @Slot(int, int)
    def model_download_progress(self, received: int, total: int) -> None:
        self.model_progress.setValue(int(received / total * 100))
        self.model_status.setText(f"已接收 {received / 1024**2:.1f} / {total / 1024**2:.1f} MB，完成后校验完整性。")

    @Slot(object)
    def model_installed(self, path: Path) -> None:
        key = self.active_model_key
        self.model_labels[key].setText("已准备 · SHA-256 校验通过")
        self.model_status.setText(f"{key} 模型已安装，可返回「批量字幕」开始处理。")

    def model_finished(self) -> None:
        self.model_stop_button.setEnabled(False)
        for b in self.model_buttons:
            b.setEnabled(True)
        self.refresh_start_enabled()
        if self.model_cancel.is_set():
            self.model_status.setText("模型准备已取消，临时文件已清理。可点击下载重试。")
        elif "已安装" not in self.model_status.text():
            self.model_status.setText("准备已结束。若未安装成功，请检查错误提示并点击下载重试。")

    def build_settings(self) -> None:
        layout = self.page("设置与环境检查", "发行包应自带处理组件。出现缺失时，可重新解压完整软件包，或选择受信任的组件目录。")
        self.health_text = QTextBrowser()
        layout.addWidget(self.health_text, 1)
        row = QHBoxLayout()
        self.health_button = button("重新检查环境", self.run_health, True)
        row.addWidget(self.health_button)
        self.component_button = button("修复：选择组件文件夹", self.choose_components)
        row.addWidget(self.component_button)
        row.addWidget(button("打开本地数据 / 日志", self.open_data))
        layout.addLayout(row)
        info = QLabel("组件修复只选择完整发行包的 vendor 文件夹；不要运行来源不明的 EXE。\n"
                      "设置与历史记录位于当前用户的数据目录；不需要管理员权限。")
        info.setWordWrap(True)
        layout.addWidget(info)

    def choose_components(self) -> None:
        if "health" in self.threads:
            return
        folder = QFileDialog.getExistingDirectory(self, "选择包含 ffmpeg、ffprobe、whisper-cli 的组件文件夹")
        if not folder:
            return
        import sys
        suffix = ".exe" if sys.platform == "win32" else ""
        paths = {name: Path(folder) / (name + suffix) for name in ["ffmpeg", "ffprobe", "whisper-cli"]}
        if any(not p.is_file() for p in paths.values()):
            self.show_error("此目录缺少必要组件，请选择完整软件包内的 vendor 文件夹。")
            return
        self.settings.ffmpeg, self.settings.ffprobe = str(paths["ffmpeg"]), str(paths["ffprobe"])
        self.settings.whisper = str(paths["whisper-cli"])
        try:
            self.settings.save()
            self.run_health()
        except Exception as exc:
            self.show_error(explain(exc))

    def run_health(self) -> None:
        if "health" in self.threads:
            return
        self.health_cancel.clear()
        settings = copy.deepcopy(self.settings)
        settings.output_dir = self.output.text().strip() or self.settings.output_dir
        self.health_button.setEnabled(False)
        self.health_text.setPlainText("正在检查组件、模型完整性、目录权限与磁盘空间…")
        self.launch("health", lambda worker: check_environment(settings, self.models, self.health_cancel),
                    result=self.health_result, finished=lambda: self.health_button.setEnabled(True))

    @Slot(object)
    def health_result(self, results) -> None:
        self.health_text.setPlainText("\n\n".join(f"{'✓' if ok else '待处理'}  {name}\n{detail}" for name, ok, detail in results))
        for name, ok, detail in results:
            for key in MODELS:
                if name == f"{key} 多语言模型":
                    self.model_labels[key].setText(detail)
        missing = [name for name, ok, _ in results[:3] if not ok]
        if missing:
            self.status.setText("缺少或无法启动处理组件：" + "、".join(missing) + "。请前往「设置」修复。")
        elif not any(ok for name, ok, _ in results if "模型" in name):
            self.status.setText("处理组件可用。首次使用请前往「模型管理」下载 base 模型，再开始生成。")

    def open_data(self) -> None:
        data_root().mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_root())))

    def build_help(self) -> None:
        layout = self.page("使用帮助", "第一次：解压完整软件包 → 打开程序 → 准备模型 → 导入音视频 → 开始生成。")
        view = QTextBrowser()
        view.setOpenExternalLinks(True)
        path = resource_root() / "docs/首次使用教程.md"
        view.setMarkdown(path.read_text(encoding="utf-8") if path.exists() else
            "首次使用请在模型管理下载 base 或 small 多语言模型。选择输出目录后点击开始生成。")
        layout.addWidget(view, 1)
        row = QHBoxLayout()
        row.addWidget(button("打开使用文档", lambda: QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(resource_root() / "docs")))))
        row.addWidget(button("第三方开源声明", self.open_notices))
        layout.addLayout(row)
        layout.addWidget(QLabel("使用 whisper.cpp / OpenAI Whisper、FFmpeg、Qt for Python 等开源技术。\n"
                               "本产品提供中文桌面交互与批量处理封装，底层模型由第三方提供。"))

    def open_notices(self) -> None:
        path = resource_root() / "THIRD_PARTY_NOTICES.md"
        if path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def closeEvent(self, event) -> None:
        if not self.threads:
            event.accept()
            return
        if not self.closing:
            if QMessageBox.question(self, "结束并退出", "仍有后台任务。退出将取消任务并清理临时文件，是否继续？") != QMessageBox.Yes:
                event.ignore()
                return
            self.closing = True
            self.stop_all()
            self.model_cancel.set()
            self.health_cancel.set()
            self.import_cancel.set()
            self.status.setText("正在安全退出；网络请求最多等待约 20 秒。请勿强制结束。")
        event.ignore()
        QTimer.singleShot(200, self.close)
