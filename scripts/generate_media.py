"""Generate original, reusable test speech. No copyrighted recordings are downloaded."""
import argparse
import platform
import shutil
import subprocess
from pathlib import Path

TEXT = "Hello, welcome to Subtitle Flow. This is a local speech recognition test. We create subtitles on your computer."


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    target=args.output.resolve()
    if platform.system()=="Windows":
        script=Path(__file__).with_name("synthesize.ps1")
        subprocess.run(["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",str(script),str(target)],check=True)
    elif program:=shutil.which("espeak-ng") or shutil.which("espeak"):
        subprocess.run([program,"-v","en-us","-s","145","-w",str(target),TEXT],check=True)
    elif platform.system()=="Darwin":
        temp=target.with_suffix(".aiff")
        subprocess.run(["say","-v","Samantha","-o",str(temp),TEXT],check=True)
        subprocess.run(["ffmpeg","-y","-i",str(temp),str(target)],check=True)
        temp.unlink()
    else:
        raise SystemExit("Install espeak-ng for test fixture synthesis (development only).")


if __name__=="__main__":
    main()
