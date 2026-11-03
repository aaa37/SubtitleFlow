# PyInstaller onedir: keep LGPL libraries replaceable, no UPX or obfuscation.
import sys
from pathlib import Path
root = Path(SPECPATH)
datas=[(str(root/'assets'),'assets'), (str(root/'docs'),'docs'),
       (str(root/'licenses'),'licenses'), (str(root/'THIRD_PARTY_NOTICES.md'),'.'),
       (str(root/'LICENSE_COMPLIANCE.md'),'.')]
# vendor contains ONLY verified locally built executables/libraries. DLLs stay adjacent.
binaries=[(str(p),'vendor') for p in (root/'vendor').glob('*') if p.suffix.lower() in {'.exe','.dll','.so','.dylib'} or (p.is_file() and p.suffix=='')]
a=Analysis([str(root/'scripts/launcher.py')], pathex=[str(root/'src')], binaries=binaries, datas=datas,
    hiddenimports=[], hookspath=[], runtime_hooks=[],
    excludes=['PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtQml','PySide6.QtQuick',
              'PySide6.QtCharts','PySide6.QtDataVisualization','PySide6.QtPdf','PySide6.QtMultimedia',
              'PySide6.QtNetwork','PySide6.QtOpenGL','PySide6.QtOpenGLWidgets','PySide6.QtTest'],
    noarchive=False)
if sys.platform == 'win32':
    sys.path.insert(0, str(root/'scripts'))
    from qt_bundle import prune_windows_qt, verify_no_network_import
    a.binaries = prune_windows_qt(a.binaries)
    verify_no_network_import(a.binaries)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='SubtitleFlow',debug=False,strip=False,upx=False,
    console=False,icon=str(root/'assets/icon.ico') if sys.platform=='win32' else None,
    version=str(root/'scripts/version_info.txt') if sys.platform=='win32' else None,
    manifest=str(root/'scripts/windows.manifest') if sys.platform=='win32' else None,
    contents_directory='_internal')
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='SubtitleFlow')
