from pathlib import Path
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QMessageBox, QHeaderView)
from ..errors import explain
from ..editing import save_edits
from ..subtitles import Segment, validate, timestamp, parse_timestamp


class SubtitleEditor(QDialog):
    def __init__(self, segments: list[Segment], outputs: list[Path], parent=None) -> None:
        super().__init__(parent)
        self.outputs = outputs
        self.setWindowTitle("编辑字幕 · 字幕工坊")
        self.resize(920, 560)
        root = QVBoxLayout(self)
        root.addWidget(QLabel("双击修改文本或时间；时间格式为 00:00:01,500。保存会更新此任务已导出的全部格式。"))
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["开始时间", "结束时间", "字幕文本"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 150)
        root.addWidget(self.table)
        for segment in segments:
            self.add(segment)
        row = QHBoxLayout()
        for label, callback in [("添加一行", lambda: self.add(Segment(0, 1, "新字幕"))),
                                ("删除选中行", self.remove), ("保存修改", self.save)]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            row.addWidget(button)
        root.addLayout(row)

    def add(self, segment: Segment) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)
        for c, text in enumerate([timestamp(segment.start), timestamp(segment.end), segment.text]):
            self.table.setItem(r, c, QTableWidgetItem(text))

    def remove(self) -> None:
        for row in sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True):
            self.table.removeRow(row)

    def save(self) -> None:
        try:
            segments = validate([Segment(parse_timestamp(self.table.item(r, 0).text()),
                parse_timestamp(self.table.item(r, 1).text()), self.table.item(r, 2).text())
                for r in range(self.table.rowCount())])
            if not segments:
                raise ValueError("至少保留一行字幕。")
            if QMessageBox.question(self, "保存字幕", "用修改后的内容覆盖此任务的字幕文件？") != QMessageBox.Yes:
                return
            backup = save_edits(self.outputs, segments)
            QMessageBox.information(self, "已保存", f"字幕已保存，修改前的完整原文件在：\n{backup}")
        except Exception as exc:
            QMessageBox.warning(self, "无法保存", explain(exc))
