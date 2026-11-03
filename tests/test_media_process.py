import shutil
import wave
import sys
import threading
import time
from pathlib import Path
import pytest
from subtitleflow.media import MediaAdapter, discover, ensure_writable
from subtitleflow.process import ProcessRunner
from subtitleflow.errors import AppError, Cancelled


def test_import_chinese_extensions_folders(tmp_path):
    folder=tmp_path/"中文 路径"/"子目录"
    folder.mkdir(parents=True)
    paths=[]
    for ext in ["MP4","mov","mkv","mp3","wav","m4a","pdf"]:
        p=folder/("视频 "+"长"*50+"."+ext)
        p.touch()
        paths.append(p)
    result=discover([folder.parent,paths[0]])
    assert len(result)==6
    assert all(p.is_absolute() for p in result)


def tools():
    ffmpeg=shutil.which("ffmpeg")
    ffprobe=shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("FFmpeg unavailable")
    return MediaAdapter(Path(ffmpeg),Path(ffprobe))


@pytest.mark.integration
def test_actual_extract_chinese_path(tmp_path):
    media=tools()
    src=tmp_path/"中文 音频.wav"
    with wave.open(str(src), 'wb') as wav:
        wav.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        wav.writeframes(b'\x01\x00' * 16000)
    info=media.probe(src,threading.Event())
    assert info.audio and info.duration==pytest.approx(1,abs=.05)
    progress=[]
    media.extract(src,tmp_path/"提取.wav",info,threading.Event(),progress.append)
    assert progress and progress[-1] > 95
    assert media.probe(tmp_path/"提取.wav",threading.Event()).duration > .9


@pytest.mark.integration
def test_actual_video_extract_chinese_path(tmp_path, make_video):
    media = tools()
    speech = Path(__file__).parent / 'fixtures/fleurs-cmn-test-1906.wav'
    src = make_video(tmp_path / '中文 视频.mp4', speech)
    cancel = threading.Event()
    info = media.probe(src, cancel)
    assert info.audio and info.duration > 1
    target = tmp_path / '中文 提取.wav'
    media.extract(src, target, info, cancel, lambda progress: None)
    with wave.open(str(target), 'rb') as wav:
        assert wav.getnchannels() == 1 and wav.getframerate() == 16000
        assert wav.getnframes() / wav.getframerate() == pytest.approx(info.duration, abs=.3)


@pytest.mark.integration
def test_no_audio_corrupt_empty(tmp_path, make_video):
    media=tools()
    src=tmp_path/"静音.mp4"
    make_video(src)
    info=media.probe(src,threading.Event())
    assert not info.audio
    with pytest.raises(AppError,match="没有音轨"):
        media.extract(src,tmp_path/"a.wav",info,threading.Event(),lambda x:None)
    src.write_bytes(b"broken video")
    with pytest.raises(AppError):
        media.probe(src,threading.Event())
    src.write_bytes(b"")
    with pytest.raises(AppError,match="为空"):
        media.probe(src,threading.Event())


def test_real_process_cancel_reaps(tmp_path):
    event=threading.Event()
    errors=[]
    def run():
        try:
            ProcessRunner().run(Path(sys.executable),["-u","-c","import time; print('ready'); time.sleep(30)"],
                                event,lambda line:event.set())
        except Exception as exc:
            errors.append(exc)
    worker=threading.Thread(target=run)
    started=time.monotonic()
    worker.start()
    worker.join(5)
    assert not worker.is_alive() and isinstance(errors[0],Cancelled)
    assert time.monotonic()-started < 5


def test_safe_argument_array(tmp_path):
    value="中文 空格; $() ' \""
    out=ProcessRunner().run(Path(sys.executable),["-X","utf8","-c","import sys;print(sys.argv[1])",value],threading.Event())
    assert out==value


def test_unwritable_and_space(tmp_path,monkeypatch):
    import subtitleflow.media as module
    monkeypatch.setattr(module.tempfile,"TemporaryFile",lambda **kw:(_ for _ in ()).throw(PermissionError()))
    with pytest.raises(PermissionError):
        ensure_writable(tmp_path)


def test_low_disk(tmp_path,monkeypatch):
    import subtitleflow.media as module
    from collections import namedtuple
    usage=namedtuple("Usage","total used free")
    monkeypatch.setattr(module.shutil,"disk_usage",lambda p:usage(100,99,1))
    with pytest.raises(AppError,match="空间"):
        ensure_writable(tmp_path)


def test_missing_tool_and_nonzero_exit(tmp_path):
    with pytest.raises(AppError,match="缺少组件"):
        ProcessRunner().run(tmp_path/"not-a-tool",[],threading.Event())
    with pytest.raises(AppError,match="异常退出"):
        ProcessRunner().run(Path(sys.executable),["-c","raise SystemExit(3)"],threading.Event())
