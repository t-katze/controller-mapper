"""キャリブレーションパネル.

設計書 §4.4 軸補正 に対応.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
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


@dataclass
class AxisCalibValues:
    """1軸分のキャリブレーション値."""
    axis_index: int
    deadzone: float
    end_deadzone: float
    curve: float
    smoothing: float
    invert: bool


class AxisCalibWidget(QGroupBox):
    """1軸分のキャリブレーション設定."""

    def __init__(self, axis_index: int, axis_label: str) -> None:
        super().__init__(axis_label)
        self.axis_index = axis_index
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

    def get_values(self) -> AxisCalibValues:
        """現在の設定値を返す."""
        return AxisCalibValues(
            axis_index=self.axis_index,
            deadzone=self.deadzone.value(),
            end_deadzone=self.end_deadzone.value(),
            curve=self.curve.value(),
            smoothing=self.smoothing.value(),
            invert=self.invert.isChecked(),
        )


class CalibrationPanel(QWidget):
    """軸キャリブレーションパネル.

    Signals:
        calibration_applied: 適用ボタン押下時に (軸インデックス, 値) リストを通知する.
    """

    calibration_applied: Signal = Signal(list)

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
            w = AxisCalibWidget(i, f"Axis {i}")
            self._content_layout.addWidget(w)
            self._axis_widgets.append(w)

    def get_calibration_values(self) -> list[AxisCalibValues]:
        """すべての軸のキャリブレーション値を返す."""
        return [w.get_values() for w in self._axis_widgets]

    def _on_apply(self) -> None:
        """適用ボタン押下: キャリブレーション値をシグナルで通知する."""
        values = self.get_calibration_values()
        self.calibration_applied.emit(values)
        logger.info(
            "キャリブレーション値を適用: %d 軸",
            len(values),
        )

