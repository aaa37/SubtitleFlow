param([switch]$SkipTests)
$ErrorActionPreference = 'Stop'
function Assert-LastExit { if ($LASTEXITCODE -ne 0) { throw "Command failed: $LASTEXITCODE" } }
if (-not [Environment]::Is64BitProcess) { throw 'Use Windows x64 Python' }
python -m pip install -r requirements-build.txt
Assert-LastExit
python -m pip install -e . --no-deps --no-build-isolation
Assert-LastExit
python scripts/fetch_sources.py
Assert-LastExit
python scripts/fetch_legal_sources.py
Assert-LastExit
cmake -S .work/sources/whisper.cpp-1.9.5 -B .work/whisper-win -A x64 `
  -DGGML_NATIVE=OFF -DGGML_SSE42=OFF -DGGML_AVX=OFF -DGGML_AVX2=OFF -DGGML_FMA=OFF -DGGML_F16C=OFF -DGGML_BMI2=OFF `
  -DGGML_OPENMP=OFF -DBUILD_SHARED_LIBS=OFF -DWHISPER_BUILD_TESTS=OFF
Assert-LastExit
cmake --build .work/whisper-win --config Release --target whisper-cli --parallel 2
Assert-LastExit
New-Item -ItemType Directory -Force vendor | Out-Null
Copy-Item .work/whisper-win/bin/Release/whisper-cli.exe vendor/
# UTF-8 ACP is necessary for the pinned engine's narrow argv/audio output paths on Windows.
mt.exe -nologo -manifest scripts/windows.manifest '-outputresource:vendor/whisper-cli.exe;#1'
Assert-LastExit
if (-not (Test-Path .work/ffmpeg-install/bin/ffmpeg.exe)) {
    throw 'First run scripts/ffmpeg_msvc.sh under MSYS2 + MSVC (see BUILDING.md).'
}
Copy-Item .work/ffmpeg-install/bin/*.exe vendor/
Copy-Item .work/ffmpeg-install/bin/*.dll vendor/
foreach ($program in @('ffmpeg', 'ffprobe')) {
    mt.exe -nologo -manifest scripts/windows.manifest "-outputresource:vendor/$program.exe;#1"
    Assert-LastExit
}
& vendor/ffmpeg.exe -version
Assert-LastExit
& vendor/ffprobe.exe -version
Assert-LastExit
$configuration = (& vendor/ffmpeg.exe -buildconf 2>&1) -join "`n"
if ($configuration -match '--enable-gpl|--enable-nonfree|--enable-version3') { throw 'Unexpected FFmpeg license configuration' }
$configuration | Set-Content .work/ffmpeg-buildconf.txt -Encoding utf8
& vendor/ffmpeg.exe -L | Set-Content licenses/FFmpeg-built-license.txt -Encoding utf8
& vendor/whisper-cli.exe -h
Assert-LastExit
$env:PATH = "$((Resolve-Path vendor).Path);$env:PATH"
$env:QT_QPA_PLATFORM = 'offscreen'
if (-not $SkipTests) {
    python -m pytest -q -m 'not e2e' --junitxml=.work/windows-tests.xml
    Assert-LastExit
}
python scripts/collect_notices.py
Assert-LastExit
python -m PyInstaller --noconfirm SubtitleFlow.spec
Assert-LastExit
$env:SUBTITLEFLOW_HOME = "$PWD/.work/smoke-data"
$env:QT_QPA_PLATFORM = 'windows'
$smokeTarget = Join-Path $PWD '.work/windows-smoke.json'
$proc = Start-Process -FilePath dist/SubtitleFlow/SubtitleFlow.exe -ArgumentList '--smoke-test', ('"{0}"' -f $smokeTarget) -PassThru
if (-not $proc.WaitForExit(60000)) { $proc.Kill(); throw 'Packaged GUI smoke timed out' }
if ($proc.ExitCode -ne 0) { throw 'Packaged GUI failed to start' }
$smoke = Get-Content .work/windows-smoke.json | ConvertFrom-Json
if ($smoke.gui -ne 'ok' -or -not $smoke.icon -or -not $smoke.docs) { throw 'Packaged resources missing' }
python scripts/check_release.py
Assert-LastExit
