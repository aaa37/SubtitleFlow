# 字幕工坊 SubtitleFlow 0.1.1

Windows 本地批量字幕工具。中文桌面界面；whisper.cpp + multilingual base/small；FFmpeg 提取；SRT/VTT/TXT 导出；无需账号或收费 AI API。

**当前为 0.1.1 发行加固候选，Windows 构建及销售验收尚未完成。** 真实 Linux 转写与测试记录见 [TEST_REPORT.md](TEST_REPORT.md)。由用户自行上传 GitHub。请先阅读 [上传与自动构建](docs/上传与自动构建.md)，工作流尚未在 Windows 执行，不含 Windows EXE。

## 开发

Python 3.11–3.13（建议 3.11），安装 `requirements-build.txt` 后执行 `python -m pip install -e . --no-deps --no-build-isolation`。运行 `python -m subtitleflow.app`。开发人员可在图形设置中选择含 ffmpeg、ffprobe、whisper-cli 的组件目录，或通过本地 settings.json 指定绝对路径。终端仅用于开发，发行包面向用户只需双击 EXE。

macOS：FFmpeg 可由 `brew install ffmpeg` 准备，whisper.cpp 使用 `scripts/fetch_sources.py` 的官方校验源码构建（`cmake -S .work/sources/whisper.cpp-1.9.5 -B .work/whisper-build -DBUILD_SHARED_LIBS=OFF -DCMAKE_BUILD_TYPE=Release`，`cmake --build .work/whisper-build --target whisper-cli -j 4`）。该开发依赖不会作为 Windows 二进制混入发行包。将组件路径填入设置；GUI 下载模型，然后转写。macOS 上不能通过 PyInstaller 交叉生成 Windows EXE。

## Windows 构建

完整步骤见 [BUILDING.md](BUILDING.md)，CI 为 `.github/workflows/windows.yml`。工作流执行真实 Windows 编译、单元/媒体测试、GUI smoke、真实 ASR、冻结程序真实 ASR，然后上传候选 ZIP 与 SHA-256。任一步失败则不应发布。

普通用户的模型存放在 `%LOCALAPPDATA%/SubtitleFlow/models`。初次可通过 GUI 下载，或从官方页面获取后通过 GUI 导入。下载文件与官方 SHA-256 完整匹配后才原子安装。不会下载 `.en` 模型。没有远程上传功能，不含遥测、支付、DRM 或在线激活。

## 结构

```text
src/subtitleflow/
  app.py                 GUI 入口 / 打包诊断入口
  gui/                   窗口、后台线程、字幕编辑、设计系统
  jobs.py                顺序批处理 / 取消 / 历史
  media.py               文件发现 / FFprobe / 音轨提取
  asr.py                 whisper.cpp JSON 适配
  process.py             参数数组执行 / 超时 / 进程清理
  models.py              校验清单 / 下载 / 导入 / 原子安装
  subtitles.py           数据验证 / 时间戳 / 重名保护 / 导出
  config.py, paths.py     配置 / 用户数据 / 冻结资源路径
  storage.py             原子存储
  errors.py              中文可操作错误
  extensions.py          第二阶段模块协议
scripts/                 源码下载、Windows 构建、打包、合成媒体
.github/workflows/       Windows 构建与真实端到端测试
tests/                   单元、真实媒体、GUI、真实 ASR 测试
docs/                    用户及商业发行文档
licenses/                原始许可和构建收集的通知
assets/                  自绘图标
```

## 测试

`python -m pytest -q -m 'not e2e'`；Linux 无显示器时设置 `QT_QPA_PLATFORM=offscreen`。
真实测试：先执行 `python scripts/generate_media.py .work/speech.wav`（macOS say / Linux espeak-ng / Windows System.Speech，仅开发用），设置 `SF_WHISPER_BIN`、`SF_MODEL_BASE`、`SF_TEST_SPEECH`（可加 `SF_MODEL_SMALL` 运行 small 回归） 为实际绝对路径，运行 `python -m pytest -q -m e2e`。设置 `SUBTITLEFLOW_REQUIRE_E2E=1` 禁止依赖缺失时跳过。

不含模型权重、客户视频和来源不明的二进制。第三方来源、许可证和发行阻塞项见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)、[LICENSE_COMPLIANCE.md](LICENSE_COMPLIANCE.md)。
