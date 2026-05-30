"""エントリーポイント."""
from __future__ import annotations

import sys
from pathlib import Path

from controller_mapper.logging.log_config import setup_logging


def main() -> int:
    # ロギング設定
    log_dir = Path.home() / ".controller_mapper" / "logs"
    setup_logging(log_dir=log_dir)

    import logging
    logger = logging.getLogger(__name__)
    logger.info("Controller Mapper 起動")

    # pygame の display 初期化を抑制 (headlessモード)
    import os
    if "SDL_VIDEODRIVER" not in os.environ:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    if "SDL_AUDIODRIVER" not in os.environ:
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    from PySide6.QtWidgets import QApplication
    from controller_mapper.app.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Controller Mapper")
    app.setApplicationVersion("0.1.0")

    # SDL_VIDEODRIVER を戻す (pygame がjoystickを読む際に dummy は不要)
    # joystickはdisplayと独立して初期化できる
    if os.environ.get("SDL_VIDEODRIVER") == "dummy":
        del os.environ["SDL_VIDEODRIVER"]

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
