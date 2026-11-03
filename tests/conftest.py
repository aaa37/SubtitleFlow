import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest


@pytest.fixture
def make_video():
    """Create real MP4 fixtures without FFmpeg's optional lavfi device."""
    import math
    import json
    import shutil
    import subprocess

    def create(target, audio=None):
        duration = 1.0
        if audio is not None:
            probe = subprocess.check_output([shutil.which('ffprobe'), '-v', 'error',
                '-show_entries', 'format=duration', '-of', 'json', str(audio)])
            duration = float(json.loads(probe)['format']['duration'])
        raw = target.with_suffix('.rgb')
        raw.write_bytes(bytes(64 * 64 * 3) * math.ceil(duration * 5))
        args = [shutil.which('ffmpeg'), '-v', 'error', '-f', 'rawvideo',
                '-pixel_format', 'rgb24', '-video_size', '64x64', '-framerate', '5', '-i', str(raw)]
        if audio is not None:
            args += ['-i', str(audio), '-shortest', '-c:a', 'aac']
        try:
            subprocess.run([*args, '-c:v', 'mpeg4', str(target)], check=True)
        finally:
            raw.unlink(missing_ok=True)
        return target

    return create


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("SUBTITLEFLOW_HOME", str(tmp_path / "用户数据"))
