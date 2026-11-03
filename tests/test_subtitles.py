import re
import pytest
from subtitleflow.errors import AppError
from subtitleflow.subtitles import Segment, render, timestamp, parse_timestamp, export_new, safe_stem


@pytest.mark.parametrize("value,expected", [(0,"00:00:00,000"), (1.9996,"00:00:02,000"),
    (3661.123,"01:01:01,123"), (360001,"100:00:01,000")])
def test_timestamps(value, expected):
    assert timestamp(value) == expected
    assert parse_timestamp(expected) == pytest.approx(round(value*1000)/1000)


@pytest.mark.parametrize("value", ["00:61:00,000", "wrong", "-01:00:00,000"])
def test_invalid_time(value):
    with pytest.raises(AppError):
        parse_timestamp(value)


def test_all_exports_and_collision(tmp_path):
    segments=[Segment(0,1.5,"你好，中国"), Segment(1.5,3,"字幕测试")]
    first=export_new(tmp_path,"中文 视频",segments,["srt","vtt","txt"])
    second=export_new(tmp_path,"中文 视频",segments,["srt","vtt","txt"])
    assert set(first).isdisjoint(second)
    assert "你好" in first[0].read_text(encoding="utf-8")
    assert re.search(r"00:00:00,000 --> 00:00:01,500", first[0].read_text(encoding="utf-8"))
    assert first[1].read_text(encoding="utf-8").startswith("WEBVTT\n\n")
    assert "00:00:01.500" in first[1].read_text(encoding="utf-8")
    assert first[2].read_text(encoding="utf-8") == "你好，中国\n字幕测试\n"


def test_rollback_preserves_existing(tmp_path, monkeypatch):
    import subtitleflow.subtitles as module
    original=tmp_path/"片子.srt"
    original.write_text("用户原文",encoding="utf-8")
    def fail(*args):
        raise PermissionError("busy")
    monkeypatch.setattr(module,"atomic_write",fail)
    with pytest.raises(PermissionError):
        export_new(tmp_path,"片子",[Segment(0,1,"你好")],["srt","vtt"])
    assert list(tmp_path.iterdir()) == [original]
    assert original.read_text(encoding="utf-8") == "用户原文"


@pytest.mark.parametrize("segments", [[Segment(-1,2,"x")], [Segment(2,1,"x")],
    [Segment(0,1,"")], [Segment(float("nan"),1,"x")]])
def test_invalid_segments(segments):
    with pytest.raises(AppError):
        render(segments,"srt")


def test_reserved_names_and_vtt():
    assert safe_stem("CON")=="_CON"
    assert "/" not in safe_stem("a/b")
    assert "&lt;" in render([Segment(0,1,"<hello>")],"vtt")
    assert len(safe_stem("长"*300)) <= 90
