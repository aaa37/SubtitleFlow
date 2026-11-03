"""Package an auditable Windows candidate or reviewed release."""
import argparse
import json
import shutil
import zipfile
from pathlib import Path
from subtitleflow import __version__
from subtitleflow.release_checks import require_x64_pe, verify_frozen_evidence, audit_qt_modules, sha256
from fetch_sources import SOURCES as ENGINE_SOURCES
from fetch_legal_sources import SOURCES as QT_SOURCES


def copy_verified(source: Path, target: Path, expected: str) -> None:
    if not source.is_file() or sha256(source) != expected:
        raise SystemExit(f"Missing or invalid corresponding source: {source.name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sale", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    bundle = root / "dist/SubtitleFlow"
    executable = bundle / "SubtitleFlow.exe"
    # Preserve the complete DLL inventory even if a subsequent audit blocks ZIP creation.
    from check_release import main as inventory
    inventory()
    require_x64_pe(executable)
    modules = audit_qt_modules(bundle)
    if args.sale:
        review = json.loads((root / "release-review.json").read_text(encoding="utf-8"))
        required = ["windows10_clean_machine", "windows11_clean_machine", "packaged_real_asr",
                    "qt_replaceability_test", "licenses_and_sources_reviewed", "commercial_terms_reviewed"]
        if any(review.get(key) is not True for key in required) or not review.get("support_contact"):
            raise SystemExit("Release review incomplete; see docs/发布检查表.md")
        verify_frozen_evidence(root / ".work/windows-smoke.json", executable)
        verify_frozen_evidence(root / ".work/frozen-e2e/result.json", executable, asr=True)
    legal = bundle / "OpenSource"
    sources = legal / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    for path in [root / "THIRD_PARTY_NOTICES.md", root / "LICENSE_COMPLIANCE.md"]:
        shutil.copyfile(path, legal / path.name)
    for _key, (_url, digest, name) in ENGINE_SOURCES.items():
        copy_verified(root / ".work/sources" / name, sources / name, digest)
    for name, (_base, digest) in QT_SOURCES.items():
        copy_verified(root / ".work/legal-sources" / name, sources / name, digest)
    shutil.copyfile(root / ".work/legal-sources/sources.json", sources / "sources.json")
    for name in ["ffmpeg_msvc.sh", "build_windows.ps1", "fetch_sources.py", "fetch_legal_sources.py"]:
        shutil.copyfile(root / "scripts" / name, sources / name)
    with zipfile.ZipFile(legal / "application-source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for folder in ["src", "scripts", "assets", "docs", "licenses", "tests", ".github"]:
            for path in sorted((root / folder).rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts and not path.name.endswith(".pyc"):
                    archive.write(path, path.relative_to(root))
        for name in ["pyproject.toml", "requirements-build.txt", "SubtitleFlow.spec", "BUILDING.md"]:
            archive.write(root / name, name)
    for name in ["用户安装说明.md", "售后与使用条款.md", "开源库替换说明.md"]:
        shutil.copyfile(root / "docs" / name, bundle / name)
    evidence_dir = bundle / "BuildEvidence"
    evidence_dir.mkdir(exist_ok=True)
    for name in ["windows-smoke.json", "ffmpeg-buildconf.txt", "windows-tests.xml", "windows-e2e-tests.xml"]:
        path = root / ".work" / name
        if path.is_file():
            shutil.copyfile(path, evidence_dir / name)
    asr = root / ".work/frozen-e2e/result.json"
    if asr.is_file():
        shutil.copyfile(asr, evidence_dir / "frozen-asr.json")
    (evidence_dir / "release-manifest.json").write_text(json.dumps({
        "version": __version__, "mode": "release" if args.sale else "candidate",
        "exe_sha256": sha256(executable), "qt_modules": modules, "sources_bundled": True}, indent=2), encoding="utf-8")
    marker = bundle / "候选版_未完成销售验收.txt"
    if args.sale:
        marker.unlink(missing_ok=True)
    else:
        marker.write_text("候选构建：Windows 真机验收与最终发行审查未完成，不得作为已验证正式版发售。\n", encoding="utf-8")
    inventory()
    mode = "release" if args.sale else "candidate"
    prefix = root / "dist" / f"SubtitleFlow-{__version__}-windows-x64-{mode}"
    archive = Path(shutil.make_archive(str(prefix), "zip", bundle.parent, bundle.name))
    archive.with_suffix(".zip.sha256").write_text(f"{sha256(archive)}  {archive.name}\n", encoding="ascii")
    print(archive)
    print(sha256(archive))


if __name__ == "__main__":
    main()
