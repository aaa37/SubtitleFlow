import sys
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
from .gui.window import MainWindow
from .logging_setup import configure
from .paths import resource_root, data_root
from .instance import acquire_instance
from .diagnostics import runtime_facts
from .storage import write_json


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("SubtitleFlow")
    app.setOrganizationName("SubtitleFlow")
    try:
        instance_lock = acquire_instance(data_root())
        configure()
        if "--self-test" in sys.argv:
            from .selftest import run
            return run(sys.argv[sys.argv.index("--self-test") + 1:])
        smoke = "--smoke-test" in sys.argv
        window = MainWindow(startup_check=not smoke)
        window.show()
        if smoke:
            def finish() -> None:
                target = Path(sys.argv[sys.argv.index("--smoke-test") + 1])
                write_json(target, {"gui": "ok", "resources": str(resource_root()),
                    "icon": (resource_root() / "assets/icon.svg").is_file(),
                    "docs": (resource_root() / "docs/首次使用教程.md").is_file(), "runtime": runtime_facts()})
                app.quit()
            QTimer.singleShot(500, finish)
        result = app.exec()
        instance_lock.unlock()
        return result
    except Exception as exc:
        if any(flag in sys.argv for flag in ("--smoke-test", "--self-test")):
            import logging
            logging.getLogger(__name__).exception("Packaged diagnostic failed")
            return 1
        QMessageBox.critical(None, "字幕工坊无法启动", f"请重新解压软件包，或联系卖家。\n{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
