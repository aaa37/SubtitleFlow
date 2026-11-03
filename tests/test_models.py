import hashlib
import io
import threading
import urllib.error
import pytest
import subtitleflow.models as module
from subtitleflow.errors import AppError, Cancelled


@pytest.fixture
def manager(tmp_path, monkeypatch):
    content=b"verified test model"
    spec=module.ModelSpec("base","测试",len(content),hashlib.sha256(content).hexdigest())
    monkeypatch.setitem(module.MODELS,"base",spec)
    return module.ModelManager(tmp_path/"models"), content


def test_download_verified_atomic(manager):
    m,content=manager
    progress=[]
    target=m.install("base",threading.Event(),lambda *v:progress.append(v),opener=lambda *a,**k:io.BytesIO(content))
    assert target.read_bytes()==content
    assert m.ready("base",threading.Event())
    assert progress[-1]==(len(content),len(content))
    assert list(m.folder.iterdir())==[target]


def test_download_bad_hash_preserves_previous(manager):
    m,content=manager
    m.folder.mkdir()
    m.path("base").write_bytes(content)
    with pytest.raises(AppError,match="校验失败"):
        m.install("base",threading.Event(),lambda *v:None,opener=lambda *a,**k:io.BytesIO(b"x"*len(content)))
    assert m.path("base").read_bytes()==content
    assert not list(m.folder.glob("*.part"))


def test_download_no_network(manager):
    m,_=manager
    def offline(*args,**kwargs):
        raise urllib.error.URLError("offline")
    with pytest.raises(AppError,match="网络"):
        m.install("base",threading.Event(),lambda *v:None,opener=offline)
    assert not list(m.folder.iterdir())


def test_cancel_missing_and_local_import(manager,tmp_path):
    m,content=manager
    assert not m.ready("base",threading.Event())
    source=tmp_path/"下载模型.bin"
    source.write_bytes(content)
    event=threading.Event()
    event.set()
    with pytest.raises(Cancelled):
        m.install("base",event,lambda *v:None,local=source)
    event.clear()
    m.install("base",event,lambda *v:None,local=source)
    assert m.ready("base",event)


def test_interrupted_read_cleans_partial(manager):
    m,_=manager
    class Broken(io.BytesIO):
        def read(self,*args):
            raise ConnectionError("lost")
    with pytest.raises(AppError):
        m.install("base",threading.Event(),lambda *v:None,opener=lambda *a,**k:Broken())
    assert not list(m.folder.iterdir())
