# 第三方开源许可声明

字幕工坊使用下列第三方技术。语音识别模型由 OpenAI 提供，C/C++ 推理由 whisper.cpp 提供；不得宣称底层模型为字幕工坊独立研发。本应用不调用 OpenAI 付费 API。

| 组件 | 固定版本 / 来源 | 许可与发行方式 |
|---|---|---|
| whisper.cpp（含 ggml / 自带解码辅助代码） | v1.9.5，https://github.com/ggml-org/whisper.cpp | MIT 为主；保留源码中的第三方 BSD/MIT 等 notice。自行从官方源码编译，源码档随候选包提供。原始 LICENSE 见 licenses/whisper.cpp-MIT.txt。 |
| OpenAI Whisper base / small 多语言权重 | 官方转换仓库固定修订 5359861c739e955e79d9a303bcbc70fb988958b1，https://huggingface.co/ggerganov/whisper.cpp | 原始代码和模型权重按 OpenAI MIT 声明；见 https://github.com/openai/whisper 及 licenses/OpenAI-Whisper-MIT.txt。由用户主动下载/导入，完整 SHA-256 校验，不包含在源码仓库和基础 ZIP 内。 |
| PySide6 / Shiboken6 | 6.8.3，Qt 官方 PyPI 包 | LGPLv3 / GPLv3 / 商业许可，发行选择适用 LGPLv3 的路径。动态库可替换、不使用 GPL-only 模块。精确 notices 由 collect_notices.py 从安装包收集。 |
| Qt Core / Gui / Widgets 与实际图像、平台插件 | 6.8.3 | 按各文件 LGPLv3、BSD、MIT 等具体许可。需要审计冻结包实际 DLL / plugin 清单及对应源码。源码提供义务见 LICENSE_COMPLIANCE.md。 |
| FFmpeg / FFprobe / libav* / libsw* | 7.1.5，https://github.com/FFmpeg/FFmpeg/tree/n7.1.5 | 自行构建 LGPL 2.1+ 配置；明确禁用 GPL、nonfree、version3、外部自动探测。CLI 独立进程。包含 COPYING.LGPLv2.1、完整对应源码和构建命令。|
| CPython | 开发环境 3.12；Windows runner 3.11 系列，实际补丁号写入构建记录 | PSF 许可与附带第三方通知；完整 LICENSE 随 Windows 构建收集。用户无需安装 Python。 |
| PyInstaller | 6.12.0 | GPLv2+，带引导加载器商业分发例外；保留完整许可和例外。并不要求应用自动使用 GPL。仅作为构建工具/引导加载器。 |
| pyinstaller-hooks-contrib | 2025.1 | 构建钩子 GPLv2+，运行时钩子按 upstream 明确的许可/例外；保留原始通知。 |
| altgraph / packaging | 0.17.4 / 24.2 | MIT / BSD-2-Clause 或 Apache-2.0；按上游文本，主要构建依赖。 |
| pytest / pytest-qt / ruff / CMake / MSYS2 工具 | requirements-build.txt / runner | 开发测试工具，非用户运行时；不随产品单独打包。 |
| Microsoft Visual C++ runtime（若 PyInstaller 收集） | 以实际 Windows 产物为准 | Microsoft 可再发行条款；发行方需审核其使用、分发资格与原始通知。不能以开源许可替代。 |

应用自身图标为本项目用 SVG 几何图形绘制，无外购素材。英文测试语音使用本项目原创文字经操作系统语音工具 / espeak-ng 合成；中文测试摘录 Google FLEURS（CC BY 4.0）一个样本并保留署名，详见 tests/fixtures/README.md。测试合成工具和测试素材不装入用户运行包。

许可文本副本见 licenses/；Windows 构建将对应 whisper.cpp / FFmpeg 源档放在 OpenSource/sources。Qt/PySide 的对应源码提供与实际运行库审计，尚需发行方完成；本清单不表示已经取得所有商业发行条件。
