"""Download fixed official source archives; validate SHA-256 before extraction."""
import hashlib
import shutil
import os
import tempfile
import tarfile
import urllib.request
from pathlib import Path

SOURCES = {
    "whisper": ("https://codeload.github.com/ggml-org/whisper.cpp/tar.gz/refs/tags/v1.9.5",
                "ff1a9053feb509ff9d7729703355541ae9690073a6b1c40eb692c962e0dc1720", "whisper.tar.gz"),
    "ffmpeg": ("https://codeload.github.com/FFmpeg/FFmpeg/tar.gz/refs/tags/n7.1.5",
               "e3963a50831c985933e1a625ed566ec4c7adb5c012c34fa9f84438e1d61bdacc", "ffmpeg-7.1.5.tar.gz"),
}


def fetch(root: Path) -> None:
    root.mkdir(parents=True,exist_ok=True)
    for key,(url,digest,name) in SOURCES.items():
        archive=root/name
        actual = ""
        if archive.is_file():
            with archive.open("rb") as source:
                actual = hashlib.file_digest(source, "sha256").hexdigest()
        if actual != digest:
            fd, temporary_name = tempfile.mkstemp(dir=root, suffix=".part")
            os.close(fd)
            temporary = Path(temporary_name)
            try:
                with urllib.request.urlopen(url, timeout=60) as src, temporary.open("wb") as dest:
                    shutil.copyfileobj(src, dest)
                with temporary.open("rb") as source:
                    actual = hashlib.file_digest(source, "sha256").hexdigest()
                if actual != digest:
                    raise RuntimeError(f"{name}: source SHA-256 mismatch")
                os.replace(temporary, archive)
            finally:
                temporary.unlink(missing_ok=True)
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                destination=(root/member.name).resolve()
                if not destination.is_relative_to(root.resolve()) or member.issym() or member.islnk():
                    raise RuntimeError("Unsafe archive member")
            tar.extractall(root,filter="data")
        print(f"{key}: source verified")


if __name__=="__main__":
    fetch(Path(".work/sources"))
