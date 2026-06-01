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

_OUTPUT_AXIS_BAR_STYLE = (
    "QProgressBar {"
    "  border: 1px solid #064e3b; border-radius: 3px;"
    "  background: #0f1f35; text-align: center; color: #e0e0e0; font-size: 11px;"
    "}"
    "QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
    "  stop:0 #065f46, stop:1 #10b981); border-radius: 2px; }"
)

_BTN_ON_STYLE = (
    "QLabel { background: #10b981; color: white; border-radius: 4px;"
    " font-size: 10px; font-weight: bold; padding: 2px 6px; }"
)
_BTN_OFF_STYLE = (
    "QLabel { background: #374151; color: #9ca3af; border-radius: 4px;"
    " font-size: 10px; padding: 2px 6px; }"
)

_OUTPUT_EMPTY_STYLE = "color: #64748b; font-size: 11px; padding: 4px 0;"


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


class _OutputAxisRow(QWidget):
    """仮想デバイス出力の1軸分の表示行."""

    def __init__(self, label: str) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 1, 2, 1)
        layout.setSpacing(6)

        self._name_lbl = QLabel(label.upper())
        self._name_lbl.setFixedWidth(70)
        self._name_lbl.setStyleSheet("color: #10b981; font-size: 11px; font-weight: bold;")
        layout.addWidget(self._name_lbl)

        self._bar = QProgressBar()
        self._bar.setRange(0, 1000)
        self._bar.setValue(500)
        self._bar.setFixedHeight(14)
        self._bar.setStyleSheet(_OUTPUT_AXIS_BAR_STYLE)
        self._bar.setTextVisible(False)
        layout.addWidget(self._bar, stretch=1)

        self._value_lbl = QLabel("+0.000")
        self._value_lbl.setFixedWidth(55)
        self._value_lbl.setStyleSheet("color: #6bcb77; font-size: 11px; font-family: monospace;")
        layout.addWidget(self._value_lbl)

    def update_value(self, value: float) -> None:
        self._value_lbl.setText(f"{value:+.3f}")
        bar_val = int((value + 1.0) / 2.0 * 1000)
        self._bar.setValue(max(0, min(1000, bar_val)))


class _OutputButtonGrid(QWidget):
    """仮想デバイス出力ボタンのグリッド表示."""

    def __init__(self) -> None:
        super().__init__()
        self._labels: dict[int, QLabel] = {}
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(2, 2, 2, 2)
        self._grid.setSpacing(3)

    def update_buttons(self, buttons: dict[int, bool]) -> None:
        for btn_idx in sorted(buttons):
            if btn_idx not in self._labels:
                self._add_label(btn_idx)

        for btn_idx, lbl in self._labels.items():
            visible = btn_idx in buttons
            pressed = buttons.get(btn_idx, False)
            lbl.setVisible(visible)
            lbl.setText(f"B{btn_idx}:ON" if pressed else f"B{btn_idx}")
            lbl.setStyleSheet(_BTN_ON_STYLE if pressed else _BTN_OFF_STYLE)

    def _add_label(self, btn_idx: int) -> None:
        lbl = QLabel(f"B{btn_idx}")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFixedSize(48, 20)
        lbl.setStyleSheet(_BTN_OFF_STYLE)
        cols = 8
        position = len(self._labels)
        self._grid.addWidget(lbl, position // cols, position % cols)
        self._labels[btn_idx] = lbl


class _OutputMonitorWidget(QGroupBox):
    """Monitor タブ内の仮想デバイス出力表示."""

    def __init__(self) -> None:
        super().__init__("Output (仮想デバイス)")
        self._axis_rows: dict[str, _OutputAxisRow] = {}
        self.setStyleSheet(
            "QGroupBox { color: #6bcb77; font-weight: bold; border: 1px solid #065f46;"
            " border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(4)

        self._empty_label = QLabel("")
        self._empty_label.setStyleSheet(_OUTPUT_EMPTY_STYLE)
        layout.addWidget(self._empty_label)

        self._axis_header = QWidget()
        axis_header_layout = QHBoxLayout(self._axis_header)
        axis_header_layout.setContentsMargins(0, 0, 0, 0)
        axis_header_layout.addWidget(
            QLabel("出力軸", styleSheet="color: #10b981; font-size: 11px; font-weight:bold;")
        )
        axis_header_layout.addStretch()
        axis_header_layout.addWidget(
            QLabel("値", styleSheet="color: #6bcb77; font-size: 11px;")
        )
        layout.addWidget(self._axis_header)

        self._axes_layout = QVBoxLayout()
        self._axes_layout.setSpacing(1)
        layout.addLayout(self._axes_layout)

        self._button_label = QLabel(
            "出力ボタン",
            styleSheet="color: #10b981; font-size: 11px; font-weight:bold; margin-top:4px;",
        )
        layout.addWidget(self._button_label)

        self._button_grid = _OutputButtonGrid()
        layout.addWidget(self._button_grid)
        self.set_empty_message("(出力なし: 停止中 / プロファイル未読み込み / 一致するルールなし)")

    def set_empty_message(self, text: str) -> None:
        self._empty_label.setText(text)
        self._empty_label.setVisible(True)
        self._axis_header.setVisible(False)
        self._button_label.setVisible(False)
        self._button_grid.setVisible(False)
        for row in self._axis_rows.values():
            row.setVisible(False)

    def update_output(self, output: OutputState) -> None:
        axes = output.axes
        buttons = output.buttons
        has_axes = bool(axes)
        has_buttons = bool(buttons)

        self._empty_label.setVisible(not (has_axes or has_buttons))
        if not (has_axes or has_buttons):
            self._axis_header.setVisible(False)
            self._button_label.setVisible(False)
            self._button_grid.setVisible(False)
            for row in self._axis_rows.values():
                row.setVisible(False)
            return

        self._axis_header.setVisible(has_axes)
        for axis_name in sorted(axes):
            if axis_name not in self._axis_rows:
                row = _OutputAxisRow(axis_name)
                self._axes_layout.addWidget(row)
                self._axis_rows[axis_name] = row

        for axis_name, row in self._axis_rows.items():
            visible = axis_name in axes
            row.setVisible(visible)
            if visible:
                row.update_value(axes[axis_name])

        self._button_label.setVisible(has_buttons)
        self._button_grid.setVisible(has_buttons)
        if has_buttons:
            self._button_grid.update_buttons(buttons)


class DeviceMonitorWidget(QGroupBox):
    """1デバイス分の監視ウィジェット."""

    def __init__(self, device_id: str, device_name: str,
                 num_axes: int, num_buttons: int, num_hats: int) -> None:
        super().__init__(f"{device_name} ({device_id})")
        self._device_id = device_id
        self._device_name = device_name
        self._alias: str = ""
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

    def _update_title(self) -> None:
        """グループボックスのタイトルを更新する."""
        if self._alias:
            self.setTitle(f"{self._device_name} — [{self._alias}] ({self._device_id})")
        else:
            self.setTitle(f"{self._device_name} ({self._device_id})")

    def set_alias(self, alias: str) -> None:
        """プロファイルの論理デバイス名を設定する."""
        self._alias = alias
        self._update_title()


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
        self._output_monitor = _OutputMonitorWidget()
        outer.addWidget(self._output_monitor)

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
        self._output_monitor.set_empty_message(
            "(出力なし: 停止中 / プロファイル未読み込み / 一致するルールなし)"
        )

    def set_device_aliases(self, aliases: dict[str, str]) -> None:
        """プロファイルのデバイス別名をモニタウィジェットに反映する.

        Args:
            aliases: {論理名: pygame_id} の形式.
                     例: {"x56_stick": "pygame_2", "x56_throttle": "pygame_3"}
        """
        # 逆引きマップ: pygame_id -> 論理名
        id_to_alias: dict[str, str] = {v: k for k, v in aliases.items()}
        for dev_id, widget in self._device_widgets.items():
            alias = id_to_alias.get(dev_id, "")
            widget.set_alias(alias)

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
        self._output_monitor.update_output(output)
