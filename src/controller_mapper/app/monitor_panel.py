"""入力モニタパネル.

設計書 §4.2 入力モニタ に対応.
Raw入力と加工後入力を同時表示する.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from controller_mapper.core.state import FilteredState, InputState, OutputState

logger = logging.getLogger(__name__)

_AXIS_BAR_STYLE = (
    "QProgressBar {"
    "  border: 1px solid #333; border-radius: 3px;"
    "  background: #16213e; text-align: center; color: #e0e0e0; font-size: 11px;"
    "}"
    "QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
    "  stop:0 #4c1d95, stop:1 #7c3aed); border-radius: 2px; }"
)

_BTN_ON_STYLE = (
    "QLabel { background: #10b981; color: white; border-radius: 4px;"
    " font-size: 10px; font-weight: bold; padding: 2px 6px; }"
)
_BTN_OFF_STYLE = (
    "QLabel { background: #374151; color: #9ca3af; border-radius: 4px;"
    " font-size: 10px; padding: 2px 6px; }"
)


class _AxisRow(QWidget):
    """1軸分の表示行."""

    def __init__(self, label: str) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 1, 2, 1)
        layout.setSpacing(6)

        lbl = QLabel(label)
        lbl.setFixedWidth(70)
        lbl.setStyleSheet("color: #a78bfa; font-size: 11px;")
        layout.addWidget(lbl)

        self._raw_lbl = QLabel("0.000")
        self._raw_lbl.setFixedWidth(55)
        self._raw_lbl.setStyleSheet("color: #9ca3af; font-size: 11px; font-family: monospace;")
        layout.addWidget(self._raw_lbl)

        self._bar = QProgressBar()
        self._bar.setRange(0, 1000)
        self._bar.setValue(500)
        self._bar.setFixedHeight(14)
        self._bar.setStyleSheet(_AXIS_BAR_STYLE)
        self._bar.setTextVisible(False)
        layout.addWidget(self._bar, stretch=1)

        self._out_lbl = QLabel("0.000")
        self._out_lbl.setFixedWidth(55)
        self._out_lbl.setStyleSheet("color: #6bcb77; font-size: 11px; font-family: monospace;")
        layout.addWidget(self._out_lbl)

    def update_values(self, raw: float, filtered: float) -> None:
        self._raw_lbl.setText(f"{raw:+.3f}")
        self._out_lbl.setText(f"{filtered:+.3f}")
        bar_val = int((filtered + 1.0) / 2.0 * 1000)
        self._bar.setValue(max(0, min(1000, bar_val)))


class _ButtonGrid(QWidget):
    """ボタン状態グリッド表示."""

    def __init__(self, num_buttons: int) -> None:
        super().__init__()
        self._labels: list[QLabel] = []
        grid = QGridLayout(self)
        grid.setContentsMargins(2, 2, 2, 2)
        grid.setSpacing(3)
        cols = 8
        for i in range(num_buttons):
            lbl = QLabel(f"B{i}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedSize(40, 20)
            lbl.setStyleSheet(_BTN_OFF_STYLE)
            grid.addWidget(lbl, i // cols, i % cols)
            self._labels.append(lbl)

    def update_buttons(self, buttons: dict[int, bool]) -> None:
        for i, lbl in enumerate(self._labels):
            pressed = buttons.get(i, False)
            lbl.setStyleSheet(_BTN_ON_STYLE if pressed else _BTN_OFF_STYLE)


class DeviceMonitorWidget(QGroupBox):
    """1デバイス分の監視ウィジェット."""

    def __init__(self, device_id: str, device_name: str,
                 num_axes: int, num_buttons: int, num_hats: int) -> None:
        super().__init__(f"{device_name} ({device_id})")
        self.setStyleSheet(
            "QGroupBox { color: #a78bfa; font-weight: bold; border: 1px solid #4c1d95;"
            " border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }"
        )
        layout = QVBoxLayout(self)

        # ヘッダラベル
        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("軸", styleSheet="color: #a78bfa; font-size: 11px; font-weight:bold;"))
        hdr.addWidget(QLabel("Raw", styleSheet="color: #9ca3af; font-size: 11px;"))
        hdr.addStretch()
        hdr.addWidget(QLabel("Out", styleSheet="color: #6bcb77; font-size: 11px;"))
        layout.addLayout(hdr)

        # 軸行
        self._axis_rows: list[_AxisRow] = []
        for a in range(num_axes):
            row = _AxisRow(f"Axis {a}")
            layout.addWidget(row)
            self._axis_rows.append(row)

        # ボタングリッド
        if num_buttons > 0:
            btn_lbl = QLabel("ボタン", styleSheet="color: #a78bfa; font-size: 11px; font-weight:bold; margin-top:4px;")
            layout.addWidget(btn_lbl)
            self._btn_grid = _ButtonGrid(num_buttons)
            layout.addWidget(self._btn_grid)
        else:
            self._btn_grid = None

        # Hat表示
        self._hat_labels: list[QLabel] = []
        if num_hats > 0:
            hat_row = QHBoxLayout()
            hat_row.addWidget(QLabel("Hat:", styleSheet="color: #a78bfa; font-size: 11px;"))
            for h in range(num_hats):
                lbl = QLabel("(0,0)")
                lbl.setStyleSheet("color: #ffd93d; font-family: monospace; font-size: 11px;")
                hat_row.addWidget(lbl)
                self._hat_labels.append(lbl)
            hat_row.addStretch()
            layout.addLayout(hat_row)

    def update_state(self, raw_state: dict, filtered_state: dict) -> None:
        raw_axes = raw_state.get("axes", {})
        filtered_axes = filtered_state.get("axes", {})
        for i, row in enumerate(self._axis_rows):
            row.update_values(
                raw=raw_axes.get(i, 0.0),
                filtered=filtered_axes.get(i, 0.0),
            )
        if self._btn_grid is not None:
            self._btn_grid.update_buttons(raw_state.get("buttons", {}))
        for i, lbl in enumerate(self._hat_labels):
            hat_val = raw_state.get("hats", {}).get(i, (0, 0))
            lbl.setText(str(hat_val))


class MonitorPanel(QWidget):
    """入力モニタパネル.

    すべての接続デバイスの Raw / Filtered 入力を表示する.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._device_widgets: dict[str, DeviceMonitorWidget] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)

        title = QLabel("入力モニタ  (Raw / Filtered / Output)")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #a78bfa; margin-bottom: 4px;")
        outer.addWidget(title)

        # スクロール可能エリア
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._content_layout.setSpacing(8)
        scroll.setWidget(self._content)
        outer.addWidget(scroll)

        # 出力セクション
        self._output_group = QGroupBox("Output (仮想デバイス)")
        self._output_group.setStyleSheet(
            "QGroupBox { color: #6bcb77; font-weight: bold; border: 1px solid #065f46;"
            " border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }"
        )
        self._output_layout = QVBoxLayout(self._output_group)
        self._output_axes_label = QLabel("(なし)")
        self._output_axes_label.setStyleSheet("color: #9ca3af; font-family: monospace; font-size: 11px;")
        self._output_layout.addWidget(self._output_axes_label)
        outer.addWidget(self._output_group)

    def setup_devices(self, devices: list) -> None:
        """デバイス情報からモニタウィジェットを構築する."""
        # 既存ウィジェットをクリア
        for w in self._device_widgets.values():
            self._content_layout.removeWidget(w)
            w.deleteLater()
        self._device_widgets.clear()

        for dev in devices:
            w = DeviceMonitorWidget(
                device_id=dev.device_id,
                device_name=dev.name,
                num_axes=dev.num_axes,
                num_buttons=dev.num_buttons,
                num_hats=dev.num_hats,
            )
            self._content_layout.addWidget(w)
            self._device_widgets[dev.device_id] = w

    def update_state(
        self,
        raw: InputState,
        filtered: FilteredState,
        output: OutputState,
    ) -> None:
        """GUI更新 (30〜60 Hz で呼ばれる)."""
        for dev_id, widget in self._device_widgets.items():
            raw_dev = raw.devices.get(dev_id)
            flt_dev = filtered.devices.get(dev_id)
            if raw_dev is None:
                continue
            flt_axes = flt_dev.axes if flt_dev else {}
            widget.update_state(
                raw_state={"axes": raw_dev.axes, "buttons": raw_dev.buttons, "hats": raw_dev.hats},
                filtered_state={"axes": flt_axes},
            )

        # 出力表示
        if output.axes or output.buttons:
            lines = []
            for name, val in sorted(output.axes.items()):
                lines.append(f"  {name}: {val:+.3f}")
            for idx, pressed in sorted(output.buttons.items()):
                lines.append(f"  Btn{idx}: {'ON ' if pressed else 'OFF'}")
            self._output_axes_label.setText("\n".join(lines) if lines else "(なし)")
        else:
            self._output_axes_label.setText("(ルールなし / 停止中)")
