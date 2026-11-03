"""Test Qt pruning against the complete installed Windows distribution or wheel."""
import argparse
import contextlib
import io
from pathlib import Path
import tempfile
import zipfile
from qt_bundle import prune_windows_qt, verify_qt_imports

BINDINGS = {'QtCore.pyd', 'QtGui.pyd', 'QtWidgets.pyd', 'QtSvg.pyd', 'QtSvgWidgets.pyd'}


def check(entries: list) -> None:
    with contextlib.redirect_stdout(io.StringIO()):
        retained = prune_windows_qt(entries)
    verify_qt_imports(retained)
    names = {Path(e[0].replace('\\', '/')).name for e in retained}
    assert {'Qt6Core.dll', 'Qt6Gui.dll', 'Qt6Widgets.dll', 'qwindows.dll'}.issubset(names)
    assert not {'Qt6Network.dll', 'Qt6Pdf.dll', 'Qt6VirtualKeyboard.dll'} & names
    for plugin in ['qtuiotouchplugin.dll', 'qpdf.dll', 'qtvirtualkeyboardplugin.dll']:
        bad = next(e for e in entries if Path(e[0].replace('\\', '/')).name == plugin)
        try:
            verify_qt_imports([*retained, bad])
        except RuntimeError:
            pass
        else:
            raise AssertionError(f'Missing dependency was not rejected: {plugin}')
    try:
        verify_qt_imports([e for e in retained if Path(e[0].replace('\\', '/')).name != 'Qt6Core.dll'])
    except RuntimeError:
        pass
    else:
        raise AssertionError('Missing Qt6Core.dll was not rejected')
    print(f'Qt PE preflight passed: {len(entries)} candidates, {len(retained)} retained; '
          'TUIO/PDF/virtual-keyboard/missing-core regressions rejected.')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--wheel', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        if args.wheel:
            with zipfile.ZipFile(args.wheel) as archive:
                for name in archive.namelist():
                    if not (name.endswith('.dll') or Path(name).name in BINDINGS):
                        continue
                    target = (root / name).resolve()
                    if not target.is_relative_to(root.resolve()):
                        raise ValueError('Unsafe wheel path')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(name))
        else:
            import PySide6
            root = Path(PySide6.__file__).parent.parent
        entries = [(str(p.relative_to(root)), str(p), 'BINARY') for p in (root / 'PySide6').rglob('*')
                   if p.is_file() and (p.suffix == '.dll' or p.name in BINDINGS)]
        check(entries)


if __name__ == '__main__':
    main()
