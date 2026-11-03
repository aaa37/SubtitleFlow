"""Keep only the Windows Qt plugins used by this Widgets application."""
from pathlib import Path

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
        if '/plugins/' in name:
            plugin = name.split('/plugins/', 1)[1]
            if plugin not in WINDOWS_PLUGINS:
                print(f'Omitting unused Qt plugin: {entry[0]}')
                continue
        if Path(name).name == 'qt6network.dll':
            print(f'Omitting unused Qt Network: {entry[0]}')
            continue
        retained.append(entry)
    return retained


def verify_no_network_import(entries: list) -> None:
    """Fail if pruning would break any remaining PE import, including plugins."""
    import pefile
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
            if any(item.dll.lower() == b'qt6network.dll' for item in imports):
                raise RuntimeError(f'{name} still requires Qt6Network.dll; review the Qt plugin selection')
