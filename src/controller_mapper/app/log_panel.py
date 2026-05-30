"""ログパネル.

Python logging の出力を GUIテキストエリアに表示する.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from controller_mapper.logging.log_config import QtLogHandler


class LogPanel(QWidget):
    """ログ表示パネル."""

    log_signal: Signal = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._setup_logging()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # ツールバー
        toolbar = QHBoxLayout()
        self._btn_clear = QPushButton("クリア")
        self._btn_clear.setFixedWidth(80)
        self._btn_clear.clicked.connect(self._on_clear)
        toolbar.addStretch()
        toolbar.addWidget(self._btn_clear)
        layout.addLayout(toolbar)

        # テキストエリア
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setMaximumBlockCount(2000)
        font = QFont("Consolas", 9)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._text.setFont(font)
        self._text.setStyleSheet(
            "QPlainTextEdit {"
            "  background-color: #1a1a2e;"
            "  color: #e0e0e0;"
            "  border: 1px solid #333;"
            "}"
        )
        layout.addWidget(self._text)

    def _setup_logging(self) -> None:
        handler = QtLogHandler(self.log_signal)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        ))
        logging.getLogger().addHandler(handler)
        self.log_signal.connect(self._append_log)

    def _append_log(self, msg: str) -> None:
        # レベルに応じて色を変える
        color = "#e0e0e0"
        if "[ERROR]" in msg or "[CRITICAL]" in msg:
            color = "#ff6b6b"
        elif "[WARNING]" in msg:
            color = "#ffd93d"
        elif "[INFO]" in msg:
            color = "#6bcb77"
        elif "[DEBUG]" in msg:
            color = "#a0a0a0"

        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.setCharFormat(fmt)
        cursor.insertText(msg + "\n")
        self._text.setTextCursor(cursor)
        self._text.ensureCursorVisible()

    def _on_clear(self) -> None:
        self._text.clear()
