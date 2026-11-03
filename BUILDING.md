# Windows 与 macOS 开发构建

## Windows 10/11 x64 构建机

建议使用 GitHub Actions Windows 2022 runner。目标用户为 Windows 10 1903 及以上、Windows 11 x64；更早版本尚未验证 UTF-8 activeCodePage，不承诺兼容。使用 Python 3.11 x64、Visual Studio 2022 C++ 构建工具（含 Windows SDK / mt.exe）、CMake 和 MSYS2 的 bash/make/diffutils/pkgconf。普通客户不需要这些工具。

1. 将项目放入自己的 GitHub 仓库的 main 分支，打开 Actions → Windows candidate build and real transcription → Run workflow。该仓库应由开发者创建并确认；本次没有指定远端，未擅自创建公共仓库。
2. runner 从固定官方版本和固定 SHA-256 下载源码。FFmpeg 使用 MSVC 编译共享库，不开启 GPL/nonfree/version3，不自动探测外部库，不启用网络协议。whisper.cpp 静态链接自身 MIT 组件，禁用 SSE4.2/AVX/AVX2/FMA/F16C/BMI2，优先兼容较老 CPU。没有要求 NVIDIA GPU。
3. 若在本地构建，先在 x64 Native Tools 命令环境中安装 MSYS2 工具，启动继承 MSVC PATH 的 MSYS2 bash（避免 /usr/bin/link 覆盖 MSVC link.exe；必要时把 MSVC 路径放在前面）。执行 `python scripts/fetch_sources.py`，然后 `bash scripts/ffmpeg_msvc.sh`。
4. 回到 x64 Native Tools PowerShell，执行 `./scripts/build_windows.ps1`。脚本依次安装固定依赖、构建 whisper-cli、写入 UTF-8/长路径 manifest、复制自己构建的组件、执行测试、收集通知、PyInstaller onedir、启动冻结程序 smoke、生成候选 ZIP。
5. CI 还会合成原创英文测试语音，下载并校验 base / small 多语言模型，执行英文合成语音、中文 FLEURS 真人录音真实媒体转写测试和冻结程序真实转写。模型不会装入 ZIP。若 System.Speech 没有英文语音，测试应失败，需为 runner 安装官方语音，不能换成 Mock 通过。
6. 下载 Actions artifact 内的 `SubtitleFlow-0.1.0-windows-x64-candidate.zip` 和对应 `.zip.sha256`，检查所有测试记录。上传到 GitHub artifact 不等于已公开发行。

## 验证与签名

在没有 Python/FFmpeg 的干净 Windows 10、11 虚拟机上解压，真实 GUI 下载/导入模型，处理中文路径 MP4、批量任务与坏文件，取消正在识别的任务，离线重启后再次处理。不要仅凭 runner 测试声明普通客户可用。单独验证系统用户名含中文、解压路径含中文、长路径、低配 CPU、文件占用和低磁盘空间。

Windows Authenticode 签名需要发行主体自己的证书。先对最终 EXE / 自建 DLL 签名，再重新生成 ZIP 和 SHA-256。时间戳服务器与证书选择由发行方负责。未签名程序可能触发 SmartScreen；文档不得要求用户关闭防护。

`package_release.py` 默认创建候选包。只有 `release-review.json` 所列实际验收完成，填写真实客服联系方式与对应源码提供 URL，才可执行 `python scripts/package_release.py --sale`。布尔字段只是发行检查记录，不能替代实测或合规审查。候选包内标识会在正式包构建时清理。

## macOS 持续开发

使用独立 venv，安装 requirements-build.txt，编辑安装项目。安装官方渠道 FFmpeg；校验后构建 whisper.cpp 原版源码。GUI「设置 → 修复」可选择含三个程序的目录；也可分别写入 settings.json 的 ffmpeg、ffprobe、whisper 字段。用 `python -m subtitleflow.app` 启动。Qt 6 默认处理高 DPI。开发过程中不要从 macOS 复制 Mach-O 可执行文件到 Windows vendor 目录。

静态检查：`python -m ruff check src tests scripts`。测试：`python -m pytest -q`。真实 ASR 的依赖未设置时只跳过对应测试，不能将跳过记为通过。

## 发布内容

`SubtitleFlow/SubtitleFlow.exe`、`_internal/`（Qt/Python/处理组件/资源）、`OpenSource/`（源档和通知）、中文文档。用户必须解压整个文件夹。可选用 Inno Setup 制作安装向导属于后续工作；当前采用无需管理员的 ZIP 便携包。

依赖锁包含运行、测试和构建包的精确版本；GitHub Actions 固定主版本，目前没有将 actions 全部锁到 commit SHA，也没有对所有 PyPI wheel 使用哈希锁。正式供应链加固时应补齐并检查上游安全更新。

0.1.1 发行脚本现会随包携带经固定 SHA-256 校验的 QtBase、QtSvg、PySide/Shiboken 对应源码及应用重建材料；无需仅依赖上游链接。实际 DLL 审计与 Windows 替换验收仍待完成。工作流上传方法见 docs/上传与自动构建.md。
