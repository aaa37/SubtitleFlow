#!/usr/bin/env bash
set -euo pipefail
# Run in an MSYS2 bash with the x64 MSVC developer environment on PATH.
root_dir="$(pwd)"
if [[ -n "${VCToolsInstallDir:-}" ]]; then
  export PATH="$(cygpath -u "$VCToolsInstallDir")/bin/Hostx64/x64:$PATH"
fi
command -v cl.exe
command -v link.exe
cd .work/sources/FFmpeg-n7.1.5
./configure --toolchain=msvc --arch=x86_64 --target-os=win64 \
  --prefix="$root_dir/.work/ffmpeg-install" \
  --disable-autodetect --disable-gpl --disable-nonfree --disable-version3 \
  --disable-doc --disable-debug --disable-x86asm --disable-network \
  --disable-ffplay --enable-shared --disable-static --disable-postproc \
  --disable-avdevice --disable-sdl2
make -j2
make install
