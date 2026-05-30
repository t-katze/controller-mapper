"""マッピングエディタパネル.

設計書 §5 変換ルール, §7.1 画面構成 に対応.
現バージョンではYAMLプロファイルのルールを表示する (読み取り専用).
"""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from controller_mapper.config.schema import ProfileConfig

logger = logging.getLogger(__name__)


class MappingEditor(QWidget):
    """マッピングルール一覧パネル."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._profile: ProfileConfig | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header_row = QHBoxLayout()
        title = QLabel("マッピングルール")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #38bdf8;")
        header_row.addWidget(title)
        header_row.addStretch()
        self._profile_label = QLabel("プロファイル: なし")
        self._profile_label.setStyleSheet("color: #64748b; font-size: 11px;")
        header_row.addWidget(self._profile_label)
        layout.addLayout(header_row)

        # テーブル
        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["ルール名", "モード", "入力デバイス", "入力タイプ", "変換", "出力タイプ", "フィルタ"]
        )
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(
            "QTableWidget { background: #0c1a2e; color: #e0e0e0; gridline-color: #1e3a5f; }"
            "QHeaderView::section { background: #0f3460; color: #38bdf8; padding: 4px; }"
            "QTableWidget::item:alternate { background: #0f1f35; }"
            "QTableWidget::item:selected { background: #1e40af; }"
        )
        layout.addWidget(self._table)

    def load_profile(self, profile: ProfileConfig) -> None:
        self._profile = profile
        self._profile_label.setText(f"プロファイル: {profile.name} v{profile.version}")
        self._refresh_table()

    def _refresh_table(self) -> None:
        if self._profile is None:
            return
        rules = self._profile.rules
        self._table.setRowCount(len(rules))
        for row, rule in enumerate(rules):
            self._table.setItem(row, 0, QTableWidgetItem(rule.name))
            self._table.setItem(row, 1, QTableWidgetItem(rule.mode))
            self._table.setItem(row, 2, QTableWidgetItem(rule.input.device))
            self._table.setItem(row, 3, QTableWidgetItem(
                f"{rule.input.type}[{rule.input.index}]"
            ))
            transform_desc = rule.transform.type or "passthrough"
            self._table.setItem(row, 4, QTableWidgetItem(transform_desc))
            out_desc = (f"{rule.output.type}[{rule.output.name or rule.output.index}]")
            self._table.setItem(row, 5, QTableWidgetItem(out_desc))
            filter_parts = []
            if rule.filters.debounce_ms > 0:
                filter_parts.append(f"db={rule.filters.debounce_ms}ms")
            if rule.filters.deadzone > 0:
                filter_parts.append(f"dz={rule.filters.deadzone:.2f}")
            if rule.filters.curve != 1.0:
                filter_parts.append(f"crv={rule.filters.curve:.1f}")
            self._table.setItem(row, 6, QTableWidgetItem(", ".join(filter_parts) or "-"))
