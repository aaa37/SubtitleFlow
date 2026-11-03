# 第三轮 Windows CI 与完整依赖回归

日期：2026-11-03。运行 41591867292，提交 1c64467。

Windows 基础测试 53 passed、7 deselected。PyInstaller 构建阶段的依赖检查拒绝 `Qt6Pdf.dll requires Qt6Network.dll`。本轮未执行 ASR，不能沿用第二轮的通过结果作为当前产物证据。

上轮修复遗漏：去除了 PDF 图像插件与 Network DLL，但 Analysis 已递归收集的 PDF DLL 未移除。上轮静态验证仅纳入少量 Qt 运行库，覆盖不充分。

本次按原有发行白名单筛选全部 Qt6 DLL，并移除不使用的 QML 运行组件；对所有保留 PE 的普通及延迟 Qt 导入检查完整闭包，不再只检查 Network 一个名称。缺失任何 Qt 依赖即汇总报错。发行许可白名单保持不变。

`scripts/check_qt_packaging.py` 可检查完整官方 Windows wheel，也可检查 runner 已安装的 PySide6。实际对官方 Essentials 6.8.3 Windows wheel 的 184 个候选 PE 检查：保留 33 个，闭包通过；放回 TUIO、PDF、虚拟键盘插件分别正确拒绝；移除 Core 也正确拒绝。此为静态验证，并未在 Linux 上运行 Windows DLL。

CI 将完整 Qt 检查前移到昂贵的 FFmpeg 编译之前。最终 PyInstaller Analysis 完成后仍检查实际保留的 PE，后续 Windows GUI smoke、真实 ASR、冻结 EXE ASR 和 ZIP 审核均保留，不通过跳过测试换取绿色构建。

本地完整基础回归 53 passed、7 deselected，1.94 秒；ruff 通过。下一轮 Windows 实际结果仍待执行，不标记正式销售验收完成。
