"""キャリブレーションパネル.

設計書 §4.4 軸補正 に対応.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class AxisCalibWidget(QGroupBox):
    """1軸分のキャリブレーション設定."""

    def __init__(self, axis_label: str) -> None:
        super().__init__(axis_label)
        self.setStyleSheet(
            "QGroupBox { color: #fbbf24; font-weight: bold; border: 1px solid #78350f;"
            " border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }"
        )
        form = QFormLayout(self)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        spin_style = (
            "QDoubleSpinBox { background: #1e293b; color: #e0e0e0;"
            " border: 1px solid #475569; border-radius: 4px; padding: 2px 4px; }"
        )

        self.deadzone = QDoubleSpinBox()
        self.deadzone.setRange(0.0, 1.0)
        self.deadzone.setSingleStep(0.01)
        self.deadzone.setDecimals(3)
        self.deadzone.setStyleSheet(spin_style)
        form.addRow("デッドゾーン:", self.deadzone)

        self.end_deadzone = QDoubleSpinBox()
        self.end_deadzone.setRange(0.0, 1.0)
        self.end_deadzone.setSingleStep(0.01)
        self.end_deadzone.setDecimals(3)
        self.end_deadzone.setStyleSheet(spin_style)
        form.addRow("エンドデッドゾーン:", self.end_deadzone)

        self.curve = QDoubleSpinBox()
        self.curve.setRange(0.1, 5.0)
        self.curve.setSingleStep(0.1)
        self.curve.setDecimals(2)
        self.curve.setValue(1.0)
        self.curve.setStyleSheet(spin_style)
        form.addRow("カーブ指数:", self.curve)

        self.smoothing = QDoubleSpinBox()
        self.smoothing.setRange(0.0, 0.99)
        self.smoothing.setSingleStep(0.05)
        self.smoothing.setDecimals(2)
        self.smoothing.setStyleSheet(spin_style)
        form.addRow("スムージング:", self.smoothing)

        self.invert = QCheckBox()
        self.invert.setStyleSheet("QCheckBox { color: #e0e0e0; }")
        form.addRow("反転:", self.invert)


class CalibrationPanel(QWidget):
    """軸キャリブレーションパネル."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._axis_widgets: list[AxisCalibWidget] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        title = QLabel("軸キャリブレーション")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #fbbf24; margin-bottom: 4px;")
        outer.addWidget(title)

        note = QLabel(
            "⚠ 主操縦軸にはスムージングをかけすぎないこと。\n"
            "ダイヤル・スライダー類は多めのスムージングが適切。"
        )
        note.setStyleSheet("color: #fcd34d; font-size: 11px; background: #1c1917;"
                           " border-radius: 4px; padding: 6px;")
        note.setWordWrap(True)
        outer.addWidget(note)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._content)
        outer.addWidget(scroll)

        # 適用ボタン
        self._btn_apply = QPushButton("適用")
        self._btn_apply.setStyleSheet(
            "QPushButton { background: #78350f; color: white; border-radius: 6px; padding: 6px 20px; }"
            "QPushButton:hover { background: #92400e; }"
        )
        self._btn_apply.clicked.connect(self._on_apply)
        outer.addWidget(self._btn_apply, alignment=Qt.AlignmentFlag.AlignRight)

    def setup_axes(self, num_axes: int) -> None:
        for w in self._axis_widgets:
            self._content_layout.removeWidget(w)
            w.deleteLater()
        self._axis_widgets.clear()
        for i in range(num_axes):
            w = AxisCalibWidget(f"Axis {i}")
            self._content_layout.addWidget(w)
            self._axis_widgets.append(w)

    def _on_apply(self) -> None:
        logger.info("キャリブレーション値を適用 (現バージョンはUI表示のみ)")
