"""Inspect produced files without asserting unperformed legal or platform checks."""
import hashlib
import json
from pathlib import Path


def main() -> None:
    root=Path('dist/SubtitleFlow')
    rows=[]
    for file in sorted(root.rglob('*')):
        if file.is_file():
            with file.open('rb') as stream:
                digest=hashlib.file_digest(stream,'sha256').hexdigest()
            rows.append({'path':str(file.relative_to(root)),'bytes':file.stat().st_size,'sha256':digest})
    Path('dist/file-inventory.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{len(rows)} files inventoried. Inspect every runtime DLL and license before release.')


if __name__=='__main__':
    main()
