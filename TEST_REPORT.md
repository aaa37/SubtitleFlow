# 0.1.1 测试记录

## 最新 Windows 实测（2026-11-03）

提交 fa0fdb5dc39fb93f3d53f521c0c8caa205c40081，Actions 41595322843 全部成功。

- 基础/集成：53 passed，7 deselected，2.85 秒。
- 真实 E2E：7 passed，53 deselected，1051.11 秒；模型与真实中英文输入，非 Mock。
- 冻结 EXE：原生 Windows GUI smoke 与真实语音转 SRT/VTT/TXT 通过；最终 EXE 哈希 db71102a4fc203e054c167fd1f1e28bc60602b02e6a8205ae88ce758c0e039b1。
- ZIP 已生成，完整性与 SHA-256 检查通过，见 DELIVERY_REPORT.md。
- 原始 JUnit、smoke、冻结 ASR、中英文转写记录及实际文件清单保存在 reports/windows-run4/。

环境是 Windows Server 2022 runner，并不替代干净 Windows 10/11 用户端测试。动态库替换、签名和最终销售审查未完成。

## 以下为此前 Linux 开发阶段记录

以下段落中的「本轮」「尚未验证」均指当时的 Linux 开发阶段，当前 Windows CI 状态以上述新记录为准。

# 0.1.1 测试记录说明

最终测试数据见 reports/current-full-tests.xml 和当前 reports 中的 JSON。上一版 0.1.0 的原始证据保存在 reports/0.1.0，不将旧测试冒充新版本结果。

本轮实际环境是 Linux、Python 3.12.14、PySide6 6.8.3。whisper.cpp 从固定官方 1.9.5 源码编译，并禁用 SSE4.2/AVX/AVX2/FMA/F16C/BMI2，以验证与 Windows 配置相近的 CPU 基线。真实识别使用经校验的多语言 base/small 模型；音视频测试的 FFmpeg 使用本机工具。Windows MSVC FFmpeg 构建仅具备流程，尚未验证，不能把 Linux 测试视为 Windows 通过。

新增检查：原始字节备份、编辑保存部分失败的回滚、毫秒取整零时长拒绝、单实例锁、取消未执行任务的进度/历史、PE 架构拒绝、冻结证据与 EXE 哈希绑定、不完整证据拒绝、未审查 Qt DLL 拒绝。

真实 E2E 包括原创英文合成语音转 MP4 后导出三格式、small 自动语言检测、真实 GUI 后台识别、FLEURS CC BY 4.0 中文真人 MP4 的 base/small × 中文/自动检测。数据和署名见 tests/fixtures。它们仅验证功能回归，不代表总体准确率评测。

当前 Windows 成品、Windows 10/11 真机、高 DPI、超长路径、占用/低空间与 Qt 替换等验收仍未执行。不能宣称商业 MVP 已完成。

## 实际执行结果

- 线程生命周期修复后的完整组合：57 passed，0 failed，0 skipped，约 247 秒；见 reports/current-full-tests.xml。
- 后续补充非阻塞错误弹窗回归后：51 项基础测试通过；见 reports/final-unit-tests.xml。该新增回归不在先前的 57 项计数内。
- 同一版本总计覆盖 51 个基础用例、7 个真实识别用例；不拼接或伪造一次“58 项全量”日志。
- 真实 GUI + 生命周期组合 8 项通过，15 轮窗口销毁/显式垃圾回收通过；错误弹窗不会阻塞线程清理。
- Linux PyInstaller onedir 实际构建、冻结 GUI 启动和资源检查通过；runtime 明确标注 linux/offscreen，不能代替 Windows 原生平台验证。
- 静态检查 ruff 通过。源码和 Qt 对应源码实际 SHA-256 校验见 reports/source-checksums.json。

首次组合测试的 SIGSEGV 与修复说明保留在 reports/lifecycle-fix.md，没有将该失败记为通过。最终错误弹窗修改后又单独验证真实 GUI 转写，结果另存 reports/final-gui-e2e.xml。
