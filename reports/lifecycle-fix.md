# 组合测试发现及修复

0.1.1 最终组合测试曾在真实 GUI 转写之后运行后台导入回归时发生进程 SIGSEGV（退出码 139）。单独非识别测试没有复现，因此未把单独通过作为完整通过依据。

修改：去掉 moveToThread 的独立 Worker 生命周期，采用单一 TaskThread 执行有限后台工作；结果/错误/进度仍通过 GUI 线程中的 CallbackBridge 槽传递。收到 finished 后先 wait() 等待原生线程完整退出，再释放引用、允许关闭窗口和 deleteLater。

新增回归：15 轮后台完成、窗口销毁及显式垃圾回收；与真实 GUI 转写及其他 GUI 测试组合执行。该组合 8 项已经通过；最终全量结果以 current-full-tests.xml 为准，不用旧的失败运行冒充成功。

Qt 官方线程文档明确 finished 后仍可能运行 thread_local 清理，完整同步应使用 wait：https://doc.qt.io/qtforpython-6.8/PySide6/QtCore/QThread.html 。本修改同时缩减跨线程 QObject 的销毁顺序依赖，不能仅凭 Python 堆栈证明唯一的底层崩溃原因。
