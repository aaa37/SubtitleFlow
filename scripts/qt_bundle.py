"""Keep only the Windows Qt plugins used by this Widgets application."""
from pathlib import Path
from subtitleflow.release_checks import QT_MODULES

WINDOWS_PLUGINS = {
    'platforms/qwindows.dll', 'platforms/qoffscreen.dll',
    'platforms/qminimal.dll', 'platforms/qdirect2d.dll',
    'styles/qmodernwindowsstyle.dll', 'iconengines/qsvgicon.dll',
    'imageformats/qico.dll', 'imageformats/qsvg.dll',
    'imageformats/qgif.dll', 'imageformats/qjpeg.dll',
}


def prune_windows_qt(entries: list) -> list:
    retained = []
    for entry in entries:
        name = entry[0].replace('\\', '/').lower()
        if '/qml/' in name or Path(name).name == 'pyside6qml.abi3.dll':
            print(f'Omitting unused QML runtime: {entry[0]}')
            continue
        if '/plugins/' in name:
            plugin = name.split('/plugins/', 1)[1]
            if plugin not in WINDOWS_PLUGINS:
                print(f'Omitting unused Qt plugin: {entry[0]}')
                continue
        leaf = Path(name).name
        if leaf.startswith('qt6') and leaf.endswith('.dll') and leaf[3:-4] not in QT_MODULES:
            print(f'Omitting unused Qt module: {entry[0]}')
            continue
        retained.append(entry)
    return retained


def verify_qt_imports(entries: list) -> None:
    """Check every Qt dependency against the actual retained DLL set."""
    import pefile
    available = {Path(entry[0].replace('\\', '/')).name.lower() for entry in entries}
    failures = []
    for name, source, _kind in entries:
        if not name.lower().endswith(('.dll', '.pyd', '.exe')):
            continue
        with pefile.PE(source, fast_load=True) as pe:
            pe.parse_data_directories(directories=[
                pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT'],
                pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT'],
            ])
            imports = [*getattr(pe, 'DIRECTORY_ENTRY_IMPORT', []),
                       *getattr(pe, 'DIRECTORY_ENTRY_DELAY_IMPORT', [])]
            for item in imports:
                dependency = item.dll.decode('ascii').lower()
                if dependency.startswith('qt6') and dependency.endswith('.dll') and dependency not in available:
                    failures.append(f'{name} requires missing {dependency}')
    if failures:
        raise RuntimeError('Qt dependency closure is incomplete:\n' + '\n'.join(sorted(set(failures))))
