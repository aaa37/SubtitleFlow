import sys
from subtitleflow.config import Settings
from subtitleflow.paths import resource_root, bundled_tool
from subtitleflow.gui.window import MainWindow
from subtitleflow.gui.editor import SubtitleEditor
from subtitleflow.jobs import Job
from subtitleflow.subtitles import Segment


def test_frozen_resources(tmp_path,monkeypatch):
    monkeypatch.setattr(sys,"_MEIPASS",str(tmp_path),raising=False)
    assert resource_root()==tmp_path
    assert bundled_tool("ffmpeg").parent==tmp_path/"vendor"


def test_config_roundtrip(tmp_path):
    settings=Settings(output_dir=str(tmp_path/"中文 输出"),model="small")
    settings.save()
    assert Settings.load()==settings


def test_gui_pages_and_queue(qtbot,tmp_path):
    window=MainWindow(Settings(output_dir=str(tmp_path)),startup_check=False)
    qtbot.addWidget(window)
    window.show()
    for i in range(5):
        window.navigate(i)
        assert window.stack.currentIndex()==i
    window.imported([Job(tmp_path/"中文 文件.mp4",duration=12)])
    assert window.queue_table.rowCount()==1
    assert window.queue_table.item(0,0).text()=="中文 文件.mp4"
    editor=SubtitleEditor([Segment(0,1,"可编辑字幕")],[tmp_path/"x.srt"],window)
    qtbot.addWidget(editor)
    assert editor.table.item(0,2).text()=="可编辑字幕"
    editor.table.item(0,2).setText("修改后")
    assert editor.table.item(0,2).text()=="修改后"


def test_async_import_keeps_gui_responsive(qtbot,tmp_path,monkeypatch):
    import time
    import subtitleflow.gui.window as module
    from subtitleflow.media import MediaInfo
    file=tmp_path/"中文.mp4"
    file.touch()
    def slow(*args):
        time.sleep(.15)
        return MediaInfo(2,True)
    monkeypatch.setattr(module.MediaAdapter,"probe",slow)
    window=MainWindow(Settings(output_dir=str(tmp_path)),startup_check=False)
    qtbot.addWidget(window)
    window.import_paths([file])
    window.navigate(2)
    assert window.stack.currentIndex()==2
    qtbot.waitUntil(lambda:"import" not in window.threads,timeout=5000)
    assert len(window.jobs)==1


def test_close_waits_for_background_cleanup(qtbot,tmp_path,monkeypatch):
    import time
    from PySide6.QtWidgets import QMessageBox
    from subtitleflow.errors import Cancelled
    window=MainWindow(Settings(output_dir=str(tmp_path)),startup_check=False)
    qtbot.addWidget(window)
    window.show()
    def work(worker):
        while not window.import_cancel.is_set():
            time.sleep(.02)
        raise Cancelled()
    monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.Yes)
    window.launch('import',work)
    window.close()
    qtbot.waitUntil(lambda:not window.threads,timeout=3000)
    qtbot.waitUntil(lambda:not window.isVisible(),timeout=3000)
    assert window.closing


def test_model_import_progress_and_result(qtbot,tmp_path,monkeypatch):
    from PySide6.QtCore import QThread
    from PySide6.QtWidgets import QApplication
    window=MainWindow(Settings(output_dir=str(tmp_path)),startup_check=False)
    qtbot.addWidget(window)
    delivered=[]
    original=window.model_download_progress
    def progress(received,total):
        delivered.append(QThread.currentThread()==QApplication.instance().thread())
        original(received,total)
    window.model_download_progress=progress
    def install(key,cancel,callback,local):
        callback(10,10)
        return tmp_path/'ggml-base.bin'
    monkeypatch.setattr(window.models,'install',install)
    window.prepare_model('base',tmp_path/'input.bin')
    qtbot.waitUntil(lambda:'model' not in window.threads,timeout=3000)
    assert delivered==[True]
    assert '校验通过' in window.model_labels['base'].text()
    assert window.start_button.isEnabled()


def test_repeated_background_completion_and_window_disposal(qtbot,tmp_path):
    import gc
    from PySide6.QtCore import QCoreApplication, QEvent
    for iteration in range(15):
        window=MainWindow(Settings(output_dir=str(tmp_path)),startup_check=False)
        qtbot.addWidget(window)
        observed=[]
        window.launch('lifetime',lambda task, value=iteration:value,result=observed.append)
        qtbot.waitUntil(lambda w=window:not w.threads,timeout=5000)
        assert observed==[iteration]
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
        del window
        gc.collect()


def test_background_error_does_not_block_thread_cleanup(qtbot,tmp_path):
    from subtitleflow.errors import AppError
    window=MainWindow(Settings(output_dir=str(tmp_path)),startup_check=False)
    qtbot.addWidget(window)
    def failure(task):
        raise AppError('网络测试失败，可以重试')
    window.launch('failing',failure)
    qtbot.waitUntil(lambda:not window.threads and bool(window.error_dialogs),timeout=5000)
    dialog=window.error_dialogs[0]
    assert '可以重试' in dialog.text()
    dialog.accept()
    qtbot.waitUntil(lambda:not window.error_dialogs,timeout=3000)
