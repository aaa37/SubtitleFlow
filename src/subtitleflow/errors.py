class AppError(Exception):
    """An actionable message safe to show to the end user."""


class Cancelled(AppError):
    def __init__(self) -> None:
        super().__init__("任务已取消。")


def explain(exc: Exception) -> str:
    if isinstance(exc, AppError):
        return str(exc)
    if isinstance(exc, PermissionError):
        return "没有读写权限，或文件被其他软件占用。请关闭占用程序，或选择个人文件夹后重试。"
    if isinstance(exc, OSError) and exc.errno == 28:
        return "磁盘空间不足。请清理临时目录和输出目录所在磁盘后重试。"
    if isinstance(exc, OSError):
        return f"文件或设备访问失败：{exc}"
    return f"处理失败（{type(exc).__name__}）：{exc}。可查看本地日志或联系卖家。"
