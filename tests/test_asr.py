import json
import threading
import pytest
from subtitleflow.asr import WhisperAdapter
from subtitleflow.errors import AppError


class Runner:
    def __init__(self,data):
        self.data=data
        self.args=[]
    def run(self,executable,args,cancel):
        self.args=args
        from pathlib import Path
        Path(args[args.index('-of')+1]+'.json').write_text(json.dumps(self.data),encoding='utf-8')
        return ''


def test_whisper_millisecond_offsets(tmp_path):
    model=tmp_path/'ggml-base.bin'
    model.touch()
    runner=Runner({'transcription':[{'offsets':{'from':250,'to':1250},'text':' 中文字幕 '}]})
    segments=WhisperAdapter(tmp_path/'whisper-cli',runner).transcribe(tmp_path/'audio.wav',model,'zh',threading.Event())
    assert segments[0].start==.25 and segments[0].end==1.25
    assert segments[0].text=='中文字幕'
    assert runner.args[runner.args.index('-l')+1]=='zh'


def test_empty_or_malformed_results(tmp_path):
    model=tmp_path/'base.bin'
    model.touch()
    for data in [{'transcription':[]},{'unexpected':True}]:
        with pytest.raises(AppError):
            WhisperAdapter(tmp_path/'engine',Runner(data)).transcribe(tmp_path/'a.wav',model,'auto',threading.Event())
