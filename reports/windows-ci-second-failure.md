# 第二轮 Windows CI：真实转写已通过，ZIP 门禁失败

2026-11-03，运行 41586919782，提交 7ca59f1。

实际 Windows 结果：52 项基础/集成测试通过；打包后的原生 Windows GUI smoke 通过；7 项真实 E2E 通过（1203.12 秒）；冻结 EXE 的真实转写也通过。最后 package_release.py 因 Qt6Network.dll 不在已审查模块清单而中止。未生成验收完成的 ZIP。

根因：PyInstaller Qt GUI 钩子收集额外插件。检查官方 PySide6_Essentials 6.8.3 Windows wheel 的真实 PE 导入表确认，generic/qtuiotouchplugin.dll 依赖 Qt6Network.dll。软件不使用 TUIO 触摸、Qt 网络、PDF 图像插件、QML 或虚拟键盘。

修复：Windows spec 只保留明确使用的平台、样式、SVG 图标和少量图像插件，移除多余插件和 Qt6Network.dll。逐一检查保留 PE 的普通及延迟导入，若仍依赖 Qt6Network.dll 立即停止构建。许可白名单保持原样，测试继续要求拒绝 Network 与 Charts。不会因模块可使用 LGPL 就略过对应的第三方通知审查。

直接验证官方 Windows wheel：保留 15 个 Qt 库/插件，没有残余 Qt6Network 导入；将真实 TUIO 插件放回时依赖检查正确拒绝。此项是静态 PE 检查，不冒充 Windows 启动测试。下一轮仍重新执行 Windows 启动及全部真实识别验证。

打包前先生成完整文件清单；失败 artifact 增加冻结启动、真实转写和清单，避免最终 ZIP 失败时丢失已经完成的实测证据。正式销售门禁保持未完成状态。
