"""仮想デバイス出力状態パネル.

設計書 §7.2 Output タブ に対応.
vJoy 等の仮想デバイスへの出力状態をリアルタイム表示する.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from controller_mapper.core.state import OutputState

logger = logging.getLogger(__name__)

_AXIS_BAR_STYLE = (
    "QProgressBar {"
    "  border: 1px solid #333; border-radius: 3px;"
    "  background: #16213e; text-align: center; color: #e0e0e0; font-size: 11px;"
    "}"
    "QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
    "  stop:0 #065f46, stop:1 #10b981); border-radius: 2px; }"
)

_BTN_ON_STYLE = (
    "QLabel { background: #10b981; color: white; border-radius: 4px;"
    " font-size: 10px; font-weight: bold; padding: 3px 8px;"
    " min-width: 44px; }"
)
_BTN_OFF_STYLE = (
    "QLabel { background: #374151; color: #9ca3af; border-radius: 4px;"
    " font-size: 10px; padding: 3px 8px; min-width: 44px; }"
)


class OutputPanel(QWidget):
    """仮想デバイス出力状態パネル."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._axis_bars: dict[str, tuple[QLabel, QProgressBar, QLabel]] = {}
        self._btn_labels: dict[int, QLabel] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("📤 仮想デバイス出力")
        title.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #10b981;"
        )
        layout.addWidget(title)

        desc = QLabel(
            "vJoy 等の仮想デバイスへ送信している軸値とボタン状態を表示します。"
        )
        desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # バックエンド情報
        self._backend_label = QLabel("出力バックエンド: —")
        self._backend_label.setStyleSheet(
            "color: #64748b; font-size: 12px; padding: 4px 8px;"
            " background: #0f172a; border-radius: 4px;"
        )
        layout.addWidget(self._backend_label)

        # スクロール可能エリア
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._content_layout.setSpacing(8)
        scroll.setWidget(content)

        # 軸出力セクション
        self._axes_group = QGroupBox("軸出力")
        self._axes_group.setStyleSheet(
            "QGroupBox { color: #10b981; font-weight: bold; border: 1px solid #065f46;"
            " border-radius: 8px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }"
        )
        self._axes_layout = QVBoxLayout(self._axes_group)
        self._axes_layout.setContentsMargins(12, 20, 12, 12)
        self._axes_layout.setSpacing(4)
        self._axes_placeholder = QLabel("(出力なし)")
        self._axes_placeholder.setStyleSheet("color: #64748b; font-size: 11px;")
        self._axes_layout.addWidget(self._axes_placeholder)
        self._content_layout.addWidget(self._axes_group)

        # ボタン出力セクション
        self._btns_group = QGroupBox("ボタン出力")
        self._btns_group.setStyleSheet(
            "QGroupBox { color: #10b981; font-weight: bold; border: 1px solid #065f46;"
            " border-radius: 8px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }"
        )
        self._btns_layout = QGridLayout(self._btns_group)
        self._btns_layout.setContentsMargins(12, 20, 12, 12)
        self._btns_layout.setSpacing(4)
        self._btns_placeholder = QLabel("(出力なし)")
        self._btns_placeholder.setStyleSheet("color: #64748b; font-size: 11px;")
        self._btns_layout.addWidget(self._btns_placeholder, 0, 0)
        self._content_layout.addWidget(self._btns_group)

        layout.addWidget(scroll)

    def set_backend_info(self, text: str) -> None:
        """バックエンド情報ラベルを更新する."""
        self._backend_label.setText(f"出力バックエンド: {text}")

    def update_output(self, output: OutputState) -> None:
        """出力状態を更新する."""
        self._update_axes(output.axes)
        self._update_buttons(output.buttons)

    def _update_axes(self, axes: dict[str, float]) -> None:
        """軸出力表示を更新する."""
        self._axes_placeholder.setVisible(not axes)

        # 新しい軸が増えたら行を追加
        for axis_name in sorted(axes.keys()):
            if axis_name not in self._axis_bars:
                self._add_axis_row(axis_name)

        # 値を更新
        for axis_name, (name_lbl, bar, val_lbl) in self._axis_bars.items():
            if axis_name in axes:
                val = axes[axis_name]
                bar_val = int((val + 1.0) / 2.0 * 1000)
                bar.setValue(max(0, min(1000, bar_val)))
                val_lbl.setText(f"{val:+.3f}")
                name_lbl.setVisible(True)
                bar.setVisible(True)
                val_lbl.setVisible(True)
            else:
                name_lbl.setVisible(False)
                bar.setVisible(False)
                val_lbl.setVisible(False)

    def _add_axis_row(self, axis_name: str) -> None:
        """軸行を1つ追加する."""
        row = QHBoxLayout()
        row.setSpacing(8)

        name_lbl = QLabel(axis_name.upper())
        name_lbl.setFixedWidth(60)
        name_lbl.setStyleSheet("color: #10b981; font-size: 12px; font-weight: bold;")
        row.addWidget(name_lbl)

        bar = QProgressBar()
        bar.setRange(0, 1000)
        bar.setValue(500)
        bar.setFixedHeight(16)
        bar.setStyleSheet(_AXIS_BAR_STYLE)
        bar.setTextVisible(False)
        row.addWidget(bar, stretch=1)

        val_lbl = QLabel("+0.000")
        val_lbl.setFixedWidth(60)
        val_lbl.setStyleSheet(
            "color: #6bcb77; font-size: 11px; font-family: monospace;"
        )
        row.addWidget(val_lbl)

        self._axes_layout.addLayout(row)
        self._axis_bars[axis_name] = (name_lbl, bar, val_lbl)

    def _update_buttons(self, buttons: dict[int, bool]) -> None:
        """ボタン出力表示を更新する."""
        self._btns_placeholder.setVisible(not buttons)

        # 新しいボタンが増えたら追加
        for btn_idx in sorted(buttons.keys()):
            if btn_idx not in self._btn_labels:
                self._add_button_label(btn_idx)

        # 値を更新
        for btn_idx, lbl in self._btn_labels.items():
            pressed = buttons.get(btn_idx, False)
            lbl.setText(f"B{btn_idx}: ON" if pressed else f"B{btn_idx}")
            lbl.setStyleSheet(_BTN_ON_STYLE if pressed else _BTN_OFF_STYLE)

    def _add_button_label(self, btn_idx: int) -> None:
        """ボタンラベルを1つ追加する."""
        lbl = QLabel(f"B{btn_idx}")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(_BTN_OFF_STYLE)
        cols = 8
        existing = len(self._btn_labels)
        self._btns_layout.addWidget(lbl, existing // cols + 1, existing % cols)
        self._btn_labels[btn_idx] = lbl
