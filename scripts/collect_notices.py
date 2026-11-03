"""Collect exact installed package notices; fail instead of silently omitting them."""
import importlib.metadata
import json
import platform
import shutil
import sys
from pathlib import Path

PACKAGES=["PySide6","PySide6_Essentials","shiboken6","pyinstaller","pyinstaller-hooks-contrib","altgraph","packaging"]


def main():
    folder=Path('licenses/python-packages')
    folder.mkdir(parents=True,exist_ok=True)
    records=[]
    for name in PACKAGES:
        dist=importlib.metadata.distribution(name)
        files=[p for p in dist.files or [] if ('license' in str(p).lower() or 'copying' in str(p).lower())
               and '.dist-info/' in str(p)]
        if not files:
            # Qt 6.8.3 wheels omit license texts from RECORD. Ship the texts from
            # the exact official v6.8.3 source tag; corresponding-source review
            # remains a separate mandatory release gate.
            if name in {"PySide6", "PySide6_Essentials", "shiboken6"} and dist.version == "6.8.3":
                source = Path("licenses/Qt-PySide6-6.8.3")
                if not (source / "LGPL-3.0-only.txt").is_file():
                    raise RuntimeError("Missing pinned Qt license texts")
                shutil.copytree(source, folder / name / "licenses", dirs_exist_ok=True)
            else:
                raise RuntimeError(f'Missing license files for {name}')
        for file in files:
            target=folder/name/str(file).split('.dist-info/',1)[1]
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(dist.locate_file(file),target)
        records.append({'package':name,'version':dist.version})
    # CPython embeds additional third party notices in its complete LICENSE file.
    candidates=[Path(sys.base_prefix)/'LICENSE.txt',Path(sys.base_prefix)/'lib'/f'python{sys.version_info.major}.{sys.version_info.minor}'/'LICENSE.txt']
    if path:=next((p for p in candidates if p.exists()),None):
        shutil.copyfile(path,Path('licenses/CPython-LICENSE.txt'))
    else:
        print('CPython license must be supplied separately before release.')
    Path('licenses/build-environment.json').write_text(json.dumps({'python':sys.version,'platform':platform.platform(),
        'packages':records},indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
