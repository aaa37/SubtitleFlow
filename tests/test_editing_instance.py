import pytest
from subtitleflow.errors import AppError
from subtitleflow.editing import save_edits
from subtitleflow.instance import acquire_instance
from subtitleflow.subtitles import Segment, export_new, render


def test_edit_backup_preserves_exact_manual_bytes(tmp_path):
    outputs=export_new(tmp_path,'字幕',[Segment(0,1,'旧')],['srt','vtt','txt'])
    original=b'\xef\xbb\xbfmanual edit\r\n'
    outputs[0].write_bytes(original)
    backup=save_edits(outputs,[Segment(0,2,'新')])
    assert (backup/outputs[0].name).read_bytes()==original
    assert '新' in outputs[0].read_text(encoding='utf-8')


def test_edit_group_rollback_on_occupied_file(tmp_path,monkeypatch):
    import subtitleflow.editing as module
    outputs=export_new(tmp_path,'字幕',[Segment(0,1,'旧')],['srt','vtt'])
    before={p:p.read_bytes() for p in outputs}
    real=module.atomic_write_bytes
    def blocked(path,content):
        if path==outputs[1]:
            raise PermissionError('occupied')
        return real(path,content)
    monkeypatch.setattr(module,'atomic_write_bytes',blocked)
    with pytest.raises(AppError,match='已还原'):
        save_edits(outputs,[Segment(0,2,'新')])
    assert all(p.read_bytes()==before[p] for p in outputs)


def test_short_cues_do_not_round_to_zero_duration():
    with pytest.raises(AppError):
        render([Segment(1,1.0001,'too short')],'srt')


def test_single_instance_release_and_reacquire(tmp_path):
    first=acquire_instance(tmp_path)
    try:
        with pytest.raises(AppError,match='已经在运行'):
            acquire_instance(tmp_path)
    finally:
        first.unlock()
    second=acquire_instance(tmp_path)
    second.unlock()
