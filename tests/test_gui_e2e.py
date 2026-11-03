import os
import shutil
import pytest
from PySide6.QtCore import QTimer
from subtitleflow.config import Settings
from subtitleflow.gui.window import MainWindow
from subtitleflow.paths import data_root


@pytest.mark.e2e
def test_real_gui_background_batch(qtbot,tmp_path):
    binary=os.environ.get('SF_WHISPER_BIN')
    model=os.environ.get('SF_MODEL_BASE')
    speech=os.environ.get('SF_TEST_SPEECH')
    if not all([binary,model,speech]):
        if os.environ.get('SUBTITLEFLOW_REQUIRE_E2E')=='1':
            pytest.fail('Real GUI ASR dependencies required')
        pytest.skip('Real speech/model not configured')
    models=data_root()/'models'
    models.mkdir(parents=True)
    shutil.copyfile(model,models/'ggml-base.bin')
    source=tmp_path/'中文 语音.wav'
    shutil.copyfile(speech,source)
    window=MainWindow(Settings(output_dir=str(tmp_path/'字幕输出'),ffmpeg=shutil.which('ffmpeg'),
        ffprobe=shutil.which('ffprobe'),whisper=binary,language='en'),startup_check=False)
    qtbot.addWidget(window)
    window.show()
    window.import_paths([source])
    qtbot.waitUntil(lambda:'import' not in window.threads,timeout=10000)
    assert len(window.jobs)==1
    window.start_batch()
    ticks=[]
    timer=QTimer()
    timer.setInterval(20)
    timer.timeout.connect(lambda:ticks.append(1))
    timer.start()
    window.navigate(2)
    qtbot.waitUntil(lambda:'batch' not in window.threads,timeout=600000)
    timer.stop()
    assert ticks, 'Qt event loop blocked during ASR'
    assert window.jobs[0].state=='已完成',window.jobs[0].error
    assert window.jobs[0].outputs[0].read_text(encoding='utf-8').strip()
