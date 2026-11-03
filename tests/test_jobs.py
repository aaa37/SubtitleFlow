from pathlib import Path
from subtitleflow.jobs import BatchEngine, HistoryStore, Job
from subtitleflow.media import MediaInfo
from subtitleflow.errors import AppError, Cancelled
from subtitleflow.subtitles import Segment


class Models:
    def ready(self,key,cancel):
        return True
    def path(self,key):
        return Path("model.bin")


class Media:
    temporary=None
    def probe(self,source,cancel):
        if "坏" in source.name:
            raise AppError("损坏")
        return MediaInfo(1,True)
    def extract(self,source,target,info,cancel,progress):
        self.temporary=target.parent
        target.write_bytes(b"audio")
        progress(100)


class ASR:
    def transcribe(self,wav,model,language,cancel):
        if cancel.is_set():
            raise Cancelled()
        return [Segment(0,1,"字幕生成成功")]


def test_failure_recovery_history_cleanup(tmp_path):
    media=Media()
    engine=BatchEngine(media,ASR(),Models(),HistoryStore(tmp_path/"history.json"))
    jobs=[Job(Path("坏视频.mp4")),Job(Path("好 视频.mp4"))]
    progress=[]
    engine.run(jobs,tmp_path/"out","base","zh",["srt","vtt","txt"],lambda j:None,lambda *x:progress.append(x))
    assert [j.state for j in jobs]==["失败","已完成"]
    assert jobs[1].outputs[0].read_text(encoding="utf-8").strip()
    assert not media.temporary.exists()
    assert progress[-1]==(2,2)
    assert len(engine.history.entries())==2


def test_cancel_current_continues(tmp_path):
    engine=BatchEngine(Media(),ASR(),Models())
    jobs=[Job(Path("a.wav")),Job(Path("b.wav"))]
    def update(job):
        if job.source.name=="a.wav" and job.state.startswith("正在识别"):
            engine.cancel_current.set()
    engine.run(jobs,tmp_path,"base","zh",["srt"],update,lambda *x:None)
    assert [j.state for j in jobs]==["已取消","已完成"]
    assert not (tmp_path/"a.srt").exists()


def test_stop_all_and_early_cancel(tmp_path):
    engine=BatchEngine(Media(),ASR(),Models())
    jobs=[Job(Path("a.wav")),Job(Path("b.wav"))]
    engine.stop()
    engine.run(jobs,tmp_path,"base","zh",["srt"],lambda j:None,lambda *x:None)
    assert all(j.state=="已取消" for j in jobs)


def test_missing_models_and_unwritable_continue(tmp_path,monkeypatch):
    models=Models()
    models.ready=lambda *x:False
    engine=BatchEngine(Media(),ASR(),models)
    jobs=[Job(Path("a.wav")),Job(Path("b.wav"))]
    engine.run(jobs,tmp_path,"base","zh",["srt"],lambda j:None,lambda *x:None)
    assert all(j.state=="失败" and "模型" in j.error for j in jobs)
    import subtitleflow.jobs as module
    monkeypatch.setattr(module,"ensure_writable",lambda *x:(_ for _ in ()).throw(PermissionError()))
    engine.models=Models()
    engine.run(jobs,tmp_path,"base","zh",["srt"],lambda j:None,lambda *x:None)
    assert all("权限" in j.error for j in jobs)


def test_timestamps_beyond_media_fail_safely(tmp_path):
    asr=ASR()
    asr.transcribe=lambda *args:[Segment(0,30,'可疑超长幻觉结果')]
    engine=BatchEngine(Media(),asr,Models())
    job=Job(Path('clip.wav'))
    engine.run([job],tmp_path,'base','zh',['srt'],lambda j:None,lambda *x:None)
    assert job.state=='失败' and '超出媒体时长' in job.error
    assert not job.outputs


def test_stop_all_counts_cancelled_waiting_jobs_and_preserves_history(tmp_path):
    history=HistoryStore(tmp_path/'history.json')
    engine=BatchEngine(Media(),ASR(),Models(),history)
    jobs=[Job(Path('a.wav')),Job(Path('b.wav'))]
    progress=[]
    engine.stop()
    engine.run(jobs,tmp_path,'base','zh',['srt'],lambda j:None,lambda *x:progress.append(x))
    assert progress[-1]==(2,2)
    assert len(history.entries())==2
