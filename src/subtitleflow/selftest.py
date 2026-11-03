"""Real frozen-build diagnostic for CI, never a substitute for GUI acceptance."""
import json
import shutil
from pathlib import Path
from .asr import WhisperAdapter
from .jobs import BatchEngine, Job
from .media import MediaAdapter
from .models import ModelManager
from .paths import bundled_tool
from .diagnostics import runtime_facts


def run(args: list[str]) -> int:
    try:
        speech, model, target = map(Path,args)
        target.mkdir(parents=True,exist_ok=True)
        source=target/"中文 音频输入.wav"
        shutil.copyfile(speech,source)
        job=Job(source)
        engine=BatchEngine(MediaAdapter(bundled_tool('ffmpeg'),bundled_tool('ffprobe')),
                           WhisperAdapter(bundled_tool('whisper-cli')),ModelManager(model.parent))
        engine.run([job],target/'中文 字幕输出','base','en',['srt','vtt','txt'],lambda j:None,lambda *x:None)
        if job.state!='已完成' or not job.segments:
            raise RuntimeError(job.error or job.state)
        (target/'result.json').write_text(json.dumps({'state':job.state,'runtime':runtime_facts(),
            'outputs':[str(p) for p in job.outputs], 'transcript':[s.text for s in job.segments]},
            ensure_ascii=False,indent=2),encoding='utf-8')
        return 0
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception('Frozen self-test failed')
        if args:
            target=Path(args[-1])
            target.mkdir(parents=True,exist_ok=True)
            (target/'error.txt').write_text(str(exc),encoding='utf-8')
        return 1
