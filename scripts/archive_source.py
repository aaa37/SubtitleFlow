"""Archive only reproducible application source, docs, fixtures and evidence."""
import hashlib
import zipfile
from pathlib import Path
from subtitleflow import __version__


def main() -> None:
    root=Path(__file__).resolve().parents[1]
    target=root/'dist'/f'SubtitleFlow-{__version__}-source.zip'
    target.parent.mkdir(exist_ok=True)
    paths=[]
    for folder in ['src','tests','scripts','assets','docs','licenses','.github','reports','vendor']:
        for file in (root/folder).rglob('*'):
            if not file.is_file() or '__pycache__' in file.parts or file.suffix in {'.pyc','.bin','.exe','.dll','.so'}:
                continue
            if any(part.endswith('.egg-info') for part in file.parts):
                continue
            if folder=='vendor' and file.name!='README.md':
                continue
            paths.append(file)
    paths.extend(p for p in root.iterdir() if p.is_file() and
                 (p.suffix in {'.md','.toml','.txt','.json','.spec'} or p.name=='.gitignore'))
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(paths)):
            archive.write(path,Path('SubtitleFlow')/path.relative_to(root))
    with zipfile.ZipFile(target) as archive:
        if archive.testzip():
            raise RuntimeError('Archive integrity check failed')
    with target.open('rb') as file:
        digest=hashlib.file_digest(file,'sha256').hexdigest()
    print(target)
    print(digest)


if __name__=='__main__':
    main()
