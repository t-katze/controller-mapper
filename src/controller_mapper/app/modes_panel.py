"""モード・レイヤー切替パネル.

設計書 §6, §7.2 に対応.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from controller_mapper.transforms.mode_switch import ModeManager

logger = logging.getLogger(__name__)

_CARD_STYLE = (
    "QGroupBox { background: #0f172a; border: 1px solid #1e293b;"
    " border-radius: 10px; margin-top: 10px; }"
    "QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px;"
    " color: #a78bfa; font-weight: bold; }"
)

_RADIO_STYLE = (
    "QRadioButton { color: #e0e0e0; font-size: 13px; spacing: 8px; padding: 6px 12px; }"
    "QRadioButton::indicator { width: 16px; height: 16px; }"
    "QRadioButton::indicator:checked { background: #a78bfa; border: 2px solid #7c3aed;"
    " border-radius: 9px; }"
    "QRadioButton::indicator:unchecked { background: #374151; border: 2px solid #4b5563;"
    " border-radius: 9px; }"
)


class ModesPanel(QWidget):
    """モード・レイヤー切替パネル.

    Signals:
        mode_changed: モードが変更されたときに新しいモード名を通知する.
    """

    mode_changed: Signal = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mode_manager: ModeManager | None = None
        self._radio_buttons: list[QRadioButton] = []
        self._button_group: QButtonGroup | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # タイトル
        title = QLabel("🎚 モード・レイヤー管理")
        title.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #a78bfa;"
        )
        layout.addWidget(title)

        desc = QLabel(
            "HOTASでは同じボタンをモード別に使いたくなるため、レイヤー機能を使います。\n"
            "プロファイル読み込み後にモード定義が反映されます。"
        )
        desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 現在モード表示
        self._current_card = QGroupBox("現在のモード")
        self._current_card.setStyleSheet(_CARD_STYLE)
        card_layout = QVBoxLayout(self._current_card)
        card_layout.setContentsMargins(16, 20, 16, 16)

        self._current_label = QLabel("—")
        self._current_label.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
            " color: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            " stop:0 #a78bfa, stop:1 #38bdf8);"
        )
        self._current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self._current_label)
        layout.addWidget(self._current_card)

        # モード選択グループ
        self._modes_group = QGroupBox("モード選択")
        self._modes_group.setStyleSheet(_CARD_STYLE)
        self._modes_layout = QVBoxLayout(self._modes_group)
        self._modes_layout.setContentsMargins(16, 20, 16, 16)

        self._no_modes_label = QLabel("プロファイルが読み込まれていません")
        self._no_modes_label.setStyleSheet("color: #64748b; font-size: 12px;")
        self._no_modes_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._modes_layout.addWidget(self._no_modes_label)
        layout.addWidget(self._modes_group)

        # ボタン行
        btn_row = QHBoxLayout()
        self._btn_cycle = QPushButton("⏭ 次のモードへ")
        self._btn_cycle.setStyleSheet(
            "QPushButton { background: #4c1d95; color: white; border-radius: 8px;"
            " padding: 10px 24px; font-size: 13px; }"
            "QPushButton:hover { background: #6d28d9; }"
            "QPushButton:disabled { background: #374151; color: #6b7280; }"
        )
        self._btn_cycle.setEnabled(False)
        self._btn_cycle.clicked.connect(self._on_cycle)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_cycle)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()

        # 切替方式の説明
        info = QGroupBox("切替方式 (設計書 §6)")
        info.setStyleSheet(_CARD_STYLE)
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(16, 20, 16, 16)
        methods = [
            "• 指定ボタンを押すたびにモード循環",
            "• 指定ボタンを押している間だけ一時レイヤー",
            "• 物理3ポジションスイッチでモード選択",
            "• 軸の位置でモード選択",
        ]
        for m in methods:
            lbl = QLabel(m)
            lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
            info_layout.addWidget(lbl)
        layout.addWidget(info)

    def set_mode_manager(self, manager: ModeManager) -> None:
        """ModeManager をセットしてUIを更新する."""
        self._mode_manager = manager
        self._rebuild_radio_buttons()
        self._update_display()
        self._btn_cycle.setEnabled(True)

    def _rebuild_radio_buttons(self) -> None:
        """ラジオボタンを再構築する."""
        # 既存のラジオボタンをクリア
        for rb in self._radio_buttons:
            self._modes_layout.removeWidget(rb)
            rb.deleteLater()
        self._radio_buttons.clear()
        if self._button_group is not None:
            self._button_group.deleteLater()

        self._no_modes_label.setVisible(self._mode_manager is None)

        if self._mode_manager is None:
            return

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        for i, mode_name in enumerate(self._mode_manager._modes):
            rb = QRadioButton(mode_name)
            rb.setStyleSheet(_RADIO_STYLE)
            if mode_name == self._mode_manager.current:
                rb.setChecked(True)
            self._button_group.addButton(rb, i)
            self._modes_layout.addWidget(rb)
            self._radio_buttons.append(rb)

        self._button_group.idClicked.connect(self._on_radio_clicked)

    def _on_radio_clicked(self, button_id: int) -> None:
        """ラジオボタンクリックでモードを変更する."""
        if self._mode_manager is None:
            return
        mode_name = self._mode_manager._modes[button_id]
        self._mode_manager.set_mode(mode_name)
        self._update_display()
        self.mode_changed.emit(mode_name)

    def _on_cycle(self) -> None:
        """次のモードへサイクルする."""
        if self._mode_manager is None:
            return
        new_mode = self._mode_manager.cycle()
        self._update_display()
        # ラジオボタンも同期
        for rb in self._radio_buttons:
            rb.setChecked(rb.text() == new_mode)
        self.mode_changed.emit(new_mode)

    def _update_display(self) -> None:
        """現在のモード表示を更新する."""
        if self._mode_manager is None:
            self._current_label.setText("—")
            return
        self._current_label.setText(self._mode_manager.current.upper())
