"""デバイス一覧パネル.

設計書 §4.1 デバイス検出 に対応.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from controller_mapper.core.state import DeviceInfo
from controller_mapper.input_backends.base import InputBackend

logger = logging.getLogger(__name__)


class DevicePanel(QWidget):
    """接続デバイス一覧パネル."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._backend: InputBackend | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # ヘッダ
        header_row = QHBoxLayout()
        title = QLabel("接続デバイス")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #a78bfa;")
        header_row.addWidget(title)
        header_row.addStretch()
        self._btn_rescan = QPushButton("🔄 再スキャン")
        self._btn_rescan.setStyleSheet(
            "QPushButton {"
            "  background: #4c1d95; color: white; border-radius: 6px; padding: 6px 14px;"
            "}"
            "QPushButton:hover { background: #6d28d9; }"
        )
        self._btn_rescan.clicked.connect(self._on_rescan)
        header_row.addWidget(self._btn_rescan)
        layout.addLayout(header_row)

        # テーブル
        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["ID", "デバイス名", "軸数", "ボタン数", "Hat数", "バックエンド", "GUID"]
        )
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(
            "QTableWidget { background: #16213e; color: #e0e0e0; gridline-color: #333; }"
            "QHeaderView::section { background: #0f3460; color: #a78bfa; padding: 4px; }"
            "QTableWidget::item:alternate { background: #1a1a2e; }"
        )
        layout.addWidget(self._table)

    def set_backend(self, backend: InputBackend) -> None:
        self._backend = backend
        self.refresh()

    def refresh(self) -> None:
        if self._backend is None:
            return
        devices = self._backend.get_devices()
        self._update_table(devices)

    def _update_table(self, devices: list[DeviceInfo]) -> None:
        self._table.setRowCount(len(devices))
        for row, dev in enumerate(devices):
            self._table.setItem(row, 0, QTableWidgetItem(dev.device_id))
            self._table.setItem(row, 1, QTableWidgetItem(dev.name))
            self._table.setItem(row, 2, QTableWidgetItem(str(dev.num_axes)))
            self._table.setItem(row, 3, QTableWidgetItem(str(dev.num_buttons)))
            self._table.setItem(row, 4, QTableWidgetItem(str(dev.num_hats)))
            self._table.setItem(row, 5, QTableWidgetItem(dev.backend_name))
            self._table.setItem(row, 6, QTableWidgetItem(dev.guid))
        logger.info("デバイス一覧を更新: %d 台", len(devices))

    def _on_rescan(self) -> None:
        if self._backend is not None:
            from controller_mapper.input_backends.pygame_backend import PygameBackend
            if isinstance(self._backend, PygameBackend):
                self._backend.rescan()
            self.refresh()
