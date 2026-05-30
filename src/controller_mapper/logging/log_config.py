"""ロギング設定."""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_dir: Path | None = None, level: int = logging.DEBUG) -> None:
    """アプリ全体のロギングを設定する.

    コンソールとファイルの両方に出力する.
    ログファイルはローテーションする.
    セキュリティ: ログにパスワード等は含まれない (本アプリはデスクトップツール).
    """
    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)

    # コンソールハンドラ
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # ファイルハンドラ (オプション)
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "controller_mapper.log"
        fh = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=2 * 1024 * 1024,  # 2MB
            backupCount=3,
            encoding="utf-8",
        )
        fh.setLevel(level)
        fh.setFormatter(fmt)
        root.addHandler(fh)
        logging.getLogger(__name__).info("ログファイル: %s", log_path)


class QtLogHandler(logging.Handler):
    """Pythonログを PySide6 シグナルに転送するハンドラ.

    GUI側の LogPanel でシグナルに接続して使う.
    """

    def __init__(self, signal: object) -> None:
        super().__init__()
        self._signal = signal

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self._signal.emit(msg)  # type: ignore[attr-defined]
        except Exception:
            self.handleError(record)
