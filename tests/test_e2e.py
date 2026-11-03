import json
import os
import re
import shutil
import subprocess
from pathlib import Path
import pytest
from subtitleflow.asr import WhisperAdapter
from subtitleflow.jobs import BatchEngine, Job
from subtitleflow.media import MediaAdapter
from subtitleflow.models import ModelManager


@pytest.mark.e2e
def test_real_speech_video_to_three_formats(tmp_path):
    binary=os.environ.get("SF_WHISPER_BIN")
    model=os.environ.get("SF_MODEL_BASE")
    speech=os.environ.get("SF_TEST_SPEECH")
    if not all([binary,model,speech]):
        if os.environ.get("SUBTITLEFLOW_REQUIRE_E2E")=="1":
            pytest.fail("Real E2E dependencies must be provided")
        pytest.skip("Set SF_WHISPER_BIN, SF_MODEL_BASE and SF_TEST_SPEECH for actual ASR")
    ffmpeg=shutil.which("ffmpeg")
    ffprobe=shutil.which("ffprobe")
    assert ffmpeg and ffprobe
    models=ModelManager(tmp_path/"中文 用户"/"模型")
    models.folder.mkdir(parents=True)
    shutil.copyfile(model,models.path("base"))
    source=tmp_path/("中文 视频 含空格 "+"长"*35+".mp4")
    subprocess.run([ffmpeg,"-v","error","-f","lavfi","-i","color=c=black:s=64x64:r=5", "-i",speech,
                    "-shortest","-c:v","mpeg4","-c:a","aac",str(source)],check=True)
    engine=BatchEngine(MediaAdapter(Path(ffmpeg),Path(ffprobe)),WhisperAdapter(Path(binary)),models)
    job=Job(source)
    engine.run([job],tmp_path/"中文 输出","base","en",["srt","vtt","txt"],lambda j:None,lambda *x:None)
    assert job.state=="已完成",job.error
    assert job.segments
    text=job.outputs[0].read_text(encoding="utf-8")
    assert re.search(r"\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}",text)
    assert any(word in text.lower() for word in ["hello","welcome","subtitle","computer","speech"])
    assert job.outputs[1].read_text(encoding="utf-8").startswith("WEBVTT")
    assert job.outputs[2].read_text(encoding="utf-8").strip()
    # A compact, reproducible evidence record with the actual transcript.
    evidence=Path(os.environ.get("SF_EVIDENCE",str(tmp_path/"evidence.json")))
    evidence.parent.mkdir(parents=True,exist_ok=True)
    evidence.write_text(json.dumps({"source":source.name,"engine":str(binary),"state":job.state,
        "segments":[{"start":s.start,"end":s.end,"text":s.text} for s in job.segments]},
        ensure_ascii=False,indent=2),encoding="utf-8")


@pytest.mark.e2e
def test_real_small_multilingual_model(tmp_path):
    binary=os.environ.get('SF_WHISPER_BIN')
    model=os.environ.get('SF_MODEL_SMALL')
    speech=os.environ.get('SF_TEST_SPEECH')
    if not all([binary,model,speech]):
        pytest.skip('Optional actual small-model regression: set SF_MODEL_SMALL')
    import threading
    media=MediaAdapter(Path(shutil.which('ffmpeg')),Path(shutil.which('ffprobe')))
    source=Path(speech)
    wav=tmp_path/'small-input.wav'
    cancel=threading.Event()
    media.extract(source,wav,media.probe(source,cancel),cancel,lambda p:None)
    segments=WhisperAdapter(Path(binary)).transcribe(wav,Path(model),'auto',cancel)
    assert segments and any('speech' in s.text.lower() for s in segments)


@pytest.mark.e2e
@pytest.mark.parametrize('key',['base','small'])
@pytest.mark.parametrize('language',['zh','auto'])
def test_real_chinese_video(tmp_path,key,language):
    binary=os.environ.get('SF_WHISPER_BIN')
    model=os.environ.get('SF_MODEL_BASE' if key=='base' else 'SF_MODEL_SMALL')
    if not binary or not model:
        pytest.skip(f'Actual {key} model not configured')
    fixture=Path(__file__).parent/'fixtures/fleurs-cmn-test-1906.wav'
    ffmpeg=shutil.which('ffmpeg')
    ffprobe=shutil.which('ffprobe')
    source=tmp_path/'中文 真人语音 测试.mp4'
    subprocess.run([ffmpeg,'-v','error','-f','lavfi','-i','color=s=64x64:r=5','-i',str(fixture),
        '-shortest','-c:v','mpeg4','-c:a','aac',str(source)],check=True)
    models=ModelManager(tmp_path/'模型')
    models.folder.mkdir(parents=True)
    shutil.copyfile(model,models.path(key))
    job=Job(source)
    engine=BatchEngine(MediaAdapter(Path(ffmpeg),Path(ffprobe)),WhisperAdapter(Path(binary)),models)
    engine.run([job],tmp_path/'输出',key,language,['srt','vtt','txt'],lambda j:None,lambda *x:None)
    assert job.state=='已完成',job.error
    text=''.join(s.text for s in job.segments)
    assert '告别' in text or '告別' in text
    assert '开始' in text or '開始' in text
    assert max(s.end for s in job.segments) <= job.duration
    evidence=Path(os.environ.get('SF_EVIDENCE',str(tmp_path/'evidence.json')))
    evidence.with_name(f'chinese-{key}-{language}.json').write_text(json.dumps({
        'model':key,'language':language,'state':job.state,'duration':job.duration,
        'transcript':text,'segments':[s.__dict__ for s in job.segments],
        'source':'Google FLEURS cmn_hans_cn/test id=1906, CC BY 4.0'},ensure_ascii=False,indent=2),encoding='utf-8')
