import json
import struct
import pytest
from subtitleflow import __version__
from subtitleflow.errors import AppError
from subtitleflow.release_checks import require_x64_pe, verify_frozen_evidence, audit_qt_modules, sha256


def test_reject_non_windows_and_wrong_arch(tmp_path):
    path=tmp_path/'app.exe'
    path.write_bytes(b'ELF wrong program')
    with pytest.raises(AppError):
        require_x64_pe(path)
    data=bytearray(256)
    data[:2]=b'MZ'
    struct.pack_into('<I',data,0x3C,128)
    data[128:132]=b'PE\0\0'
    struct.pack_into('<H',data,132,0x14c)
    path.write_bytes(data)
    with pytest.raises(AppError):
        require_x64_pe(path)


def test_evidence_bound_to_final_executable(tmp_path):
    exe=tmp_path/'app.exe'
    exe.write_bytes(b'fixture, not executable')
    proof=tmp_path/'proof.json'
    value={'gui':'ok','docs':True,'icon':True,'runtime':{'platform':'win32','qt_platform':'windows','frozen':True,
        'version':__version__,'application_sha256':sha256(exe)}}
    proof.write_text(json.dumps(value))
    verify_frozen_evidence(proof,exe)
    exe.write_bytes(b'changed after signing')
    with pytest.raises(AppError):
        verify_frozen_evidence(proof,exe)


def test_incomplete_evidence_cannot_authorize_windows_sale(tmp_path):
    exe=tmp_path/'app.exe'
    exe.write_bytes(b'fixture')
    proof=tmp_path/'proof.json'
    proof.write_text(json.dumps({'gui':'ok'}))
    with pytest.raises(AppError):
        verify_frozen_evidence(proof,exe)


@pytest.mark.parametrize('module', ['Qt6Charts.dll', 'Qt6Network.dll'])
def test_unreviewed_qt_dll_rejected(tmp_path, module):
    for name in ['Qt6Core.dll','Qt6Gui.dll','Qt6Widgets.dll']:
        (tmp_path/name).touch()
    assert len(audit_qt_modules(tmp_path))==3
    (tmp_path/module).touch()
    with pytest.raises(AppError,match='未审查'):
        audit_qt_modules(tmp_path)
