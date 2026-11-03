# 字幕工坊 0.1.1 Windows 候选包交付

2026-11-03，实际 Windows 构建已通过。测试代码提交：fa0fdb5dc39fb93f3d53f521c0c8caa205c40081。

运行：https://github.com/aaa37/SubtitleFlow/actions/runs/41595322843
产物：SubtitleFlow-0.1.1-windows-x64-candidate.zip，148222887 字节。
ZIP SHA-256：9b04093b45c9092a420d8da6c0511f1772f711637bb1eca082ef2718e07279f5
EXE SHA-256：db71102a4fc203e054c167fd1f1e28bc60602b02e6a8205ae88ce758c0e039b1

## 已核实

- Windows Server 2022 x64 runner 实际从官方固定源码编译 FFmpeg 和 whisper.cpp。
- 53 项基础/集成测试通过；7 项真实 ASR 测试通过（中英文、base/small、自动检测、GUI）。
- PyInstaller onedir EXE 在原生 Windows Qt 平台启动、图标/文档检查通过。
- 冻结 EXE 实际转写生成非空 SRT/VTT/TXT，证据与最终 EXE 哈希一致。
- ZIP 完整性检查与 SHA-256 校验通过；Qt DLL 为 Core/Gui/Widgets/Svg。
- 候选包携带 FFmpeg/whisper.cpp、QtBase/QtSvg/PySide 对应源码归档。
- 原始测试记录与证据存于 reports/windows-run4/；不把此前失败轮次计为成功。

## 使用

下载候选 ZIP，解压整个 SubtitleFlow 文件夹，双击 SubtitleFlow.exe。首次在「模型管理」下载或导入 base/small 多语言模型；模型准备完成后导入音视频，选择语言、输出目录与格式，开始生成。客户无需安装 Python。

## 尚未完成的销售验收

这是已通过 CI 的 Windows 候选包，仍保留候选版标识，不能据此直接宣称商业销售验收完成。

- 干净 Windows 10/11 客户系统的人工全流程、高 DPI、超长/中文用户名路径、取消、坏文件、离线重启验收。
- 最终 DLL/间接依赖通知审查、Qt 库替换测试、发行条款确认。
- 真实客服联系方式。代码签名尚未完成，不提供关闭防护的使用指导。

release-review.json 仅将已由本轮证据支持的 packaged_real_asr 标记为 true，其余未验收项保持 false。正式包仍受 --sale 门禁约束。当前没有支付、账号、DRM 或自动授权功能。
