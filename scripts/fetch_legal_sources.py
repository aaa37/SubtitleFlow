"""Fetch Qt corresponding source with checksums from official mirror metadata."""
import hashlib
import json
import shutil
import tempfile
import urllib.request
from pathlib import Path

SOURCES = {
    "qtbase-everywhere-src-6.8.3.tar.xz": (
        "https://download.qt.io/archive/qt/6.8/6.8.3/submodules/",
        "56001b905601bb9023d399f3ba780d7fa940f3e4861e496a7c490331f49e0b80"),
    "qtsvg-everywhere-src-6.8.3.tar.xz": (
        "https://download.qt.io/archive/qt/6.8/6.8.3/submodules/",
        "35eb516460f00f264eb504baa253432384351cf23fb9980a5857190e8deef438"),
    "pyside-setup-everywhere-src-6.8.3.tar.xz": (
        "https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.8.3-src/",
        "d2c896f7f1a6a7ea4c9f98cfe317272fd139703ddf612b86999f09e48aeef0e6"),
}


def digest(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def fetch(folder: Path = Path(".work/legal-sources")) -> dict[str, dict[str, str]]:
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, (base, sha256) in SOURCES.items():
        path = folder / name
        if not path.is_file() or digest(path) != sha256:
            errors = []
            for url in [base + name, (base + name).replace("download.qt.io/", "qt.mirror.constant.com/")]:
                with tempfile.NamedTemporaryFile(dir=folder, suffix=".part", delete=False) as temp:
                    temporary = Path(temp.name)
                try:
                    with urllib.request.urlopen(url, timeout=45) as source, temporary.open("wb") as dest:
                        shutil.copyfileobj(source, dest)
                    if digest(temporary) != sha256:
                        raise ValueError("SHA-256 mismatch")
                    temporary.replace(path)
                    break
                except Exception as exc:
                    errors.append(f"{url}: {exc}")
                finally:
                    temporary.unlink(missing_ok=True)
            else:
                raise RuntimeError("Cannot obtain verified source: " + " | ".join(errors))
        manifest[name] = {"sha256": sha256, "upstream": base + name,
                          "checksum_source": base + name + ".mirrorlist"}
        print(f"Verified corresponding source: {name}", flush=True)
    (folder / "sources.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    fetch()
