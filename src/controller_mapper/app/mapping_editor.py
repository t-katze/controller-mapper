"""マッピングエディタパネル.

設計書 §5 変換ルール, §7.1 画面構成, §13 MVP5 に対応.
GUIからルール追加・編集・削除・プロファイル保存が可能.
入力デバイス・変換タイプをドロップダウンで選択できる.
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from controller_mapper.config.loader import save_profile
from controller_mapper.config.schema import (
    FiltersConfig,
    InputConfig,
    ProfileConfig,
    RuleConfig,
    RuleOutputConfig,
    TransformConfig,
)
from controller_mapper.core.state import DeviceInfo
from controller_mapper.input_backends.base import InputBackend

logger = logging.getLogger(__name__)

_BTN_STYLE = (
    "QPushButton { border-radius: 6px; padding: 6px 14px; font-size: 12px; }"
    "QPushButton:hover { opacity: 0.9; }"
)

_LEARN_BTN_STYLE = (
    _BTN_STYLE
    + "QPushButton { background: #1e40af; color: white; min-width: 64px; }"
    "QPushButton:hover { background: #2563eb; }"
    "QPushButton:disabled { background: #1e293b; color: #64748b; }"
)

_LEARN_BTN_ACTIVE_STYLE = (
    _BTN_STYLE
    + "QPushButton { background: #78350f; color: white; min-width: 64px; }"
    "QPushButton:hover { background: #92400e; }"
)

# 変換タイプの定義 (表示名, 内部名, 説明)
_TRANSFORM_TYPES: list[tuple[str, str, str]] = [
    ("パススルー (変換なし)", "", "入力をそのまま出力する"),
    ("軸→ボタン", "axis_to_button", "軸値が閾値を超えたらボタンON"),
    ("軸(-方向)→ボタン", "axis_negative_to_button", "軸の-方向が閾値を超えたらボタンON"),
    ("軸→2ボタン (正負)", "axis_to_dual_button", "軸の正負両方向をそれぞれボタンに変換"),
    ("ボタン→軸", "button_to_axis", "ボタンON/OFFを軸値に変換"),
    ("2ボタン→軸", "buttons_to_axis", "2つのボタンで軸を操作"),
    ("ボタン分割 (ON/OFF→2ボタン)", "button_split", "ボタンのON/OFFを別々のボタンに出力"),
]

_HAT_DIRECTIONS: list[tuple[str, tuple[int, int]]] = [
    ("上", (0, 1)),
    ("右上", (1, 1)),
    ("右", (1, 0)),
    ("右下", (1, -1)),
    ("下", (0, -1)),
    ("左下", (-1, -1)),
    ("左", (-1, 0)),
    ("左上", (-1, 1)),
]


def _build_input_device_choices(
    profile_device_names: list[str],
    detected_devices: list[DeviceInfo],
) -> list[tuple[str, str]]:
    """入力デバイスコンボの表示名と保存値を作る."""
    choices: list[tuple[str, str]] = []
    seen: set[str] = set()

    for name in profile_device_names:
        if not name or name in seen:
            continue
        choices.append((name, name))
        seen.add(name)

    for dev in detected_devices:
        if not dev.device_id or dev.device_id in seen:
            continue
        label = f"{dev.name} ({dev.device_id})" if dev.name else dev.device_id
        choices.append((label, dev.device_id))
        seen.add(dev.device_id)

    return choices


def _validate_rule_for_edit(rule: RuleConfig) -> list[str]:
    """GUIで保存前に修正が必要な項目を返す."""
    errors: list[str] = []

    if not rule.name.strip():
        errors.append("ルール名を入力してください。")
    if not rule.input.device.strip():
        errors.append("入力デバイスを選択または入力してください。")
    if rule.output.type == "axis" and not rule.output.name.strip():
        errors.append("軸出力では軸名を入力してください。")

    return errors


def _input_device_display_name(device_id: str, detected_devices: list[DeviceInfo]) -> str:
    """実デバイスIDを表示用のデバイス名へ変換する."""
    for dev in detected_devices:
        if dev.device_id == device_id and dev.name:
            return dev.name
    return device_id


def _forced_io_types_for_transform(transform_type: str) -> tuple[str | None, str | None]:
    """変換タイプから強制すべき入力/出力タイプを返す."""
    if transform_type in (
        "axis_to_button",
        "axis_negative_to_button",
        "axis_to_dual_button",
    ):
        return "axis", "button"
    if transform_type == "button_to_axis":
        return None, "axis"
    if transform_type == "buttons_to_axis":
        return "button_pair", "axis"
    if transform_type == "button_split":
        return None, "button"
    return None, None


def _newly_pressed_button(
    previous: dict[str, set[int]],
    current: dict[str, set[int]],
) -> tuple[str, int] | None:
    """前回状態から新しく押されたボタンを返す."""
    for device_id in sorted(current):
        new_buttons = current[device_id] - previous.get(device_id, set())
        if new_buttons:
            return device_id, min(new_buttons)
    return None


def _newly_moved_axis(
    previous: dict[str, dict[int, float]],
    current: dict[str, dict[int, float]],
    threshold: float = 0.35,
) -> tuple[str, int, float] | None:
    """前回状態から大きく動いた軸を返す."""
    for device_id in sorted(current):
        previous_axes = previous.get(device_id, {})
        for axis_index in sorted(current[device_id]):
            value = current[device_id][axis_index]
            old_value = previous_axes.get(axis_index, value)
            if abs(value - old_value) >= threshold:
                return device_id, axis_index, value
    return None


def _newly_moved_hat(
    previous: dict[str, dict[int, tuple[int, int]]],
    current: dict[str, dict[int, tuple[int, int]]],
) -> tuple[str, int, tuple[int, int]] | None:
    """前回状態からニュートラル以外へ動いた Hat を返す."""
    for device_id in sorted(current):
        previous_hats = previous.get(device_id, {})
        for hat_index in sorted(current[device_id]):
            value = current[device_id][hat_index]
            old_value = previous_hats.get(hat_index, (0, 0))
            if value != (0, 0) and value != old_value:
                return device_id, hat_index, value
    return None


class RuleEditDialog(QDialog):
    """ルール追加・編集ダイアログ.

    入力デバイス・変換タイプをドロップダウンで選択でき、
    選択した変換タイプに応じてパラメータフィールドが動的に表示される.
    """

    def __init__(
        self,
        rule: RuleConfig | None = None,
        device_names: list[str] | None = None,
        detected_devices: list[DeviceInfo] | None = None,
        input_backend: InputBackend | None = None,
        mode_names: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("ルール編集" if rule else "ルール追加")
        self.setMinimumWidth(540)
        self.setMinimumHeight(600)
        self.setStyleSheet(
            "QDialog { background: #0f172a; color: #e0e0e0; }"
            "QLabel { color: #e0e0e0; }"
            "QGroupBox { color: #a78bfa; font-weight: bold;"
            " border: 1px solid #4c1d95; border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }"
        )

        self._rule = rule or RuleConfig()
        self._device_names = device_names or []
        self._detected_devices = detected_devices or []
        self._input_backend = input_backend
        self._device_choices = _build_input_device_choices(
            self._device_names,
            self._detected_devices,
        )
        self._mode_names = mode_names or []
        self._transform_widgets: dict[str, list[QWidget]] = {}
        self._last_out_index = self._rule.output.index
        self._populating = False
        self._learn_target: QSpinBox | None = None
        self._learn_button: QPushButton | None = None
        self._learn_target_name = ""
        self._learn_input_type = ""
        self._learn_baseline: object = {}
        self._learn_timer = QTimer(self)
        self._learn_timer.setInterval(30)
        self._learn_timer.timeout.connect(self._poll_button_learn)
        self._setup_ui()
        self._populate()

    # ─── スタイルヘルパー ───

    def _spin_style(self) -> str:
        return (
            "QDoubleSpinBox, QSpinBox { background: #1e293b; color: #e0e0e0;"
            " border: 1px solid #475569; border-radius: 4px; padding: 2px 4px; }"
        )

    def _line_style(self) -> str:
        return (
            "QLineEdit { background: #1e293b; color: #e0e0e0;"
            " border: 1px solid #475569; border-radius: 4px; padding: 4px 6px; }"
        )

    def _combo_style(self) -> str:
        return (
            "QComboBox { background: #1e293b; color: #e0e0e0;"
            " border: 1px solid #475569; border-radius: 4px; padding: 4px 6px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background: #1e293b; color: #e0e0e0;"
            " selection-background-color: #4c1d95; }"
        )

    # ─── UI構築 ───

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setSpacing(4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setSpacing(8)
        scroll.setWidget(content)

        # ─── 基本情報 ───
        basic = QGroupBox("基本情報")
        form = QFormLayout(basic)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._name_edit = QLineEdit()
        self._name_edit.setStyleSheet(self._line_style())
        self._name_edit.setPlaceholderText("例: pitch_axis, fire_button")
        form.addRow("ルール名:", self._name_edit)

        self._mode_combo = QComboBox()
        self._mode_combo.setEditable(True)
        self._mode_combo.setStyleSheet(self._combo_style())
        self._mode_combo.addItem("* (全モード共通)", "*")
        for m in self._mode_names:
            self._mode_combo.addItem(m, m)
        form.addRow("モード:", self._mode_combo)
        layout.addWidget(basic)

        # ─── 入力設定 ───
        inp_group = QGroupBox("入力")
        inp_form = QFormLayout(inp_group)
        inp_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._inp_device = QComboBox()
        self._inp_device.setEditable(True)
        self._inp_device.setStyleSheet(self._combo_style())
        for label, value in self._device_choices:
            self._inp_device.addItem(label, value)
        if not self._device_choices:
            self._inp_device.setPlaceholderText("デバイス名を入力")
        inp_form.addRow("デバイス:", self._inp_device)

        self._inp_type = QComboBox()
        self._inp_type.addItems(["axis", "button", "button_pair", "hat"])
        self._inp_type.setStyleSheet(self._combo_style())
        self._inp_type.currentTextChanged.connect(self._on_input_type_changed)
        inp_form.addRow("タイプ:", self._inp_type)

        self._inp_index = QSpinBox()
        self._inp_index.setRange(0, 127)
        self._inp_index.setStyleSheet(self._spin_style())
        self._inp_index_label = QLabel("インデックス:")
        index_row = QHBoxLayout()
        index_row.setContentsMargins(0, 0, 0, 0)
        index_row.addWidget(self._inp_index)
        self._btn_learn_index = self._make_learn_button(
            self._inp_index,
            "インデックス",
            None,
        )
        index_row.addWidget(self._btn_learn_index)
        inp_form.addRow(self._inp_index_label, index_row)

        # button_pair 用の追加フィールド
        self._inp_neg_index = QSpinBox()
        self._inp_neg_index.setRange(0, 127)
        self._inp_neg_index.setStyleSheet(self._spin_style())
        self._inp_neg_label = QLabel("-方向ボタン:")
        neg_row = QHBoxLayout()
        neg_row.setContentsMargins(0, 0, 0, 0)
        neg_row.addWidget(self._inp_neg_index)
        self._btn_learn_neg = self._make_learn_button(
            self._inp_neg_index,
            "-方向ボタン",
            "button",
        )
        neg_row.addWidget(self._btn_learn_neg)
        inp_form.addRow(self._inp_neg_label, neg_row)

        self._inp_pos_index = QSpinBox()
        self._inp_pos_index.setRange(0, 127)
        self._inp_pos_index.setValue(1)
        self._inp_pos_index.setStyleSheet(self._spin_style())
        self._inp_pos_label = QLabel("+方向ボタン:")
        pos_row = QHBoxLayout()
        pos_row.setContentsMargins(0, 0, 0, 0)
        pos_row.addWidget(self._inp_pos_index)
        self._btn_learn_pos = self._make_learn_button(
            self._inp_pos_index,
            "+方向ボタン",
            "button",
        )
        pos_row.addWidget(self._btn_learn_pos)
        inp_form.addRow(self._inp_pos_label, pos_row)

        self._hat_direction_label = QLabel("Hat方向:")
        self._hat_direction = QComboBox()
        self._hat_direction.setStyleSheet(self._combo_style())
        for label, value in _HAT_DIRECTIONS:
            self._hat_direction.addItem(f"{label} ({value[0]}, {value[1]})", value)
        inp_form.addRow(self._hat_direction_label, self._hat_direction)

        self._learn_status = QLabel("")
        self._learn_status.setStyleSheet(
            "color: #38bdf8; font-size: 11px; padding-top: 2px;"
        )
        self._learn_status.setVisible(False)
        inp_form.addRow("", self._learn_status)

        layout.addWidget(inp_group)

        # ─── 変換設定 ───
        trn_group = QGroupBox("変換")
        self._trn_layout = QFormLayout(trn_group)
        self._trn_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._trn_type = QComboBox()
        self._trn_type.setStyleSheet(self._combo_style())
        for display_name, internal_name, desc in _TRANSFORM_TYPES:
            self._trn_type.addItem(display_name, internal_name)
        self._trn_type.currentIndexChanged.connect(self._on_transform_type_changed)
        self._trn_layout.addRow("変換タイプ:", self._trn_type)

        # 変換タイプの説明ラベル
        self._trn_desc = QLabel("")
        self._trn_desc.setStyleSheet("color: #94a3b8; font-size: 11px; padding: 2px 0;")
        self._trn_desc.setWordWrap(True)
        self._trn_layout.addRow("", self._trn_desc)

        # --- 各変換タイプのパラメータウィジェット ---
        self._build_transform_params()

        layout.addWidget(trn_group)

        # ─── 出力設定 ───
        out_group = QGroupBox("出力")
        out_form = QFormLayout(out_group)
        out_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._out_type = QComboBox()
        self._out_type.addItems(["axis", "button"])
        self._out_type.setStyleSheet(self._combo_style())
        out_form.addRow("タイプ:", self._out_type)

        self._out_index = QSpinBox()
        self._out_index.setRange(0, 127)
        self._out_index.setStyleSheet(self._spin_style())
        self._out_index.valueChanged.connect(self._on_output_index_changed)
        self._out_index_label = QLabel("インデックス:")
        out_form.addRow(self._out_index_label, self._out_index)

        self._out_off_index = QSpinBox()
        self._out_off_index.setRange(0, 127)
        self._out_off_index.setValue(1)
        self._out_off_index.setStyleSheet(self._spin_style())
        self._out_off_index_label = QLabel("OFFインデックス:")
        out_form.addRow(self._out_off_index_label, self._out_off_index)

        self._out_name = QLineEdit()
        self._out_name.setStyleSheet(self._line_style())
        self._out_name.setPlaceholderText("x / y / z / rx / ry / rz / slider1 / slider2")
        out_form.addRow("軸名:", self._out_name)
        layout.addWidget(out_group)

        # ─── フィルタ設定 ───
        flt_group = QGroupBox("フィルタ")
        flt_form = QFormLayout(flt_group)
        flt_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._debounce = QDoubleSpinBox()
        self._debounce.setRange(0, 500)
        self._debounce.setSuffix(" ms")
        self._debounce.setStyleSheet(self._spin_style())
        flt_form.addRow("デバウンス:", self._debounce)

        self._deadzone = QDoubleSpinBox()
        self._deadzone.setRange(0, 1)
        self._deadzone.setSingleStep(0.01)
        self._deadzone.setDecimals(3)
        self._deadzone.setStyleSheet(self._spin_style())
        flt_form.addRow("デッドゾーン:", self._deadzone)

        self._curve = QDoubleSpinBox()
        self._curve.setRange(0.1, 5)
        self._curve.setSingleStep(0.1)
        self._curve.setDecimals(2)
        self._curve.setValue(1.0)
        self._curve.setStyleSheet(self._spin_style())
        flt_form.addRow("カーブ:", self._curve)

        self._invert = QCheckBox()
        self._invert.setStyleSheet("QCheckBox { color: #e0e0e0; }")
        flt_form.addRow("反転:", self._invert)

        self._smoothing = QDoubleSpinBox()
        self._smoothing.setRange(0, 0.99)
        self._smoothing.setSingleStep(0.05)
        self._smoothing.setDecimals(2)
        self._smoothing.setStyleSheet(self._spin_style())
        flt_form.addRow("スムージング:", self._smoothing)

        self._toggle = QCheckBox()
        self._toggle.setStyleSheet("QCheckBox { color: #e0e0e0; }")
        flt_form.addRow("トグル:", self._toggle)
        layout.addWidget(flt_group)

        outer.addWidget(scroll)

        # ─── ボタン ───
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.setStyleSheet(
            "QPushButton { background: #4c1d95; color: white; border-radius: 6px;"
            " padding: 6px 18px; }"
            "QPushButton:hover { background: #6d28d9; }"
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def _build_transform_params(self) -> None:
        """各変換タイプのパラメータウィジェットを作成する.

        _transform_widgets に { 内部名: [label, widget, label, widget, ...] } で保持し、
        変換タイプ変更時に表示/非表示を切り替える.
        """
        ss = self._spin_style()

        # --- axis_to_button / axis_negative_to_button 共通 ---
        self._atb_on_th = QDoubleSpinBox()
        self._atb_on_th.setRange(-1.0, 1.0)
        self._atb_on_th.setSingleStep(0.05)
        self._atb_on_th.setDecimals(2)
        self._atb_on_th.setValue(0.65)
        self._atb_on_th.setStyleSheet(ss)
        lbl_on = QLabel("ON閾値:")
        self._trn_layout.addRow(lbl_on, self._atb_on_th)

        self._atb_off_th = QDoubleSpinBox()
        self._atb_off_th.setRange(-1.0, 1.0)
        self._atb_off_th.setSingleStep(0.05)
        self._atb_off_th.setDecimals(2)
        self._atb_off_th.setValue(0.50)
        self._atb_off_th.setStyleSheet(ss)
        lbl_off = QLabel("OFF閾値:")
        self._trn_layout.addRow(lbl_off, self._atb_off_th)

        self._transform_widgets["axis_to_button"] = [
            lbl_on, self._atb_on_th, lbl_off, self._atb_off_th,
        ]
        # axis_negative は同じウィジェットを共有
        self._transform_widgets["axis_negative_to_button"] = [
            lbl_on, self._atb_on_th, lbl_off, self._atb_off_th,
        ]

        # --- axis_to_dual_button ---
        self._dual_neg_on = QDoubleSpinBox()
        self._dual_neg_on.setRange(-1.0, 0.0)
        self._dual_neg_on.setSingleStep(0.05)
        self._dual_neg_on.setDecimals(2)
        self._dual_neg_on.setValue(-0.60)
        self._dual_neg_on.setStyleSheet(ss)
        lbl_dn_on = QLabel("-方向 ON閾値:")
        self._trn_layout.addRow(lbl_dn_on, self._dual_neg_on)

        self._dual_neg_off = QDoubleSpinBox()
        self._dual_neg_off.setRange(-1.0, 0.0)
        self._dual_neg_off.setSingleStep(0.05)
        self._dual_neg_off.setDecimals(2)
        self._dual_neg_off.setValue(-0.45)
        self._dual_neg_off.setStyleSheet(ss)
        lbl_dn_off = QLabel("-方向 OFF閾値:")
        self._trn_layout.addRow(lbl_dn_off, self._dual_neg_off)

        self._dual_pos_on = QDoubleSpinBox()
        self._dual_pos_on.setRange(0.0, 1.0)
        self._dual_pos_on.setSingleStep(0.05)
        self._dual_pos_on.setDecimals(2)
        self._dual_pos_on.setValue(0.60)
        self._dual_pos_on.setStyleSheet(ss)
        lbl_dp_on = QLabel("+方向 ON閾値:")
        self._trn_layout.addRow(lbl_dp_on, self._dual_pos_on)

        self._dual_pos_off = QDoubleSpinBox()
        self._dual_pos_off.setRange(0.0, 1.0)
        self._dual_pos_off.setSingleStep(0.05)
        self._dual_pos_off.setDecimals(2)
        self._dual_pos_off.setValue(0.45)
        self._dual_pos_off.setStyleSheet(ss)
        lbl_dp_off = QLabel("+方向 OFF閾値:")
        self._trn_layout.addRow(lbl_dp_off, self._dual_pos_off)

        self._transform_widgets["axis_to_dual_button"] = [
            lbl_dn_on, self._dual_neg_on, lbl_dn_off, self._dual_neg_off,
            lbl_dp_on, self._dual_pos_on, lbl_dp_off, self._dual_pos_off,
        ]

        # --- button_to_axis ---
        self._bta_released = QDoubleSpinBox()
        self._bta_released.setRange(-1.0, 1.0)
        self._bta_released.setSingleStep(0.1)
        self._bta_released.setDecimals(2)
        self._bta_released.setValue(0.0)
        self._bta_released.setStyleSheet(ss)
        lbl_rel = QLabel("離した時の値:")
        self._trn_layout.addRow(lbl_rel, self._bta_released)

        self._bta_pressed = QDoubleSpinBox()
        self._bta_pressed.setRange(-1.0, 1.0)
        self._bta_pressed.setSingleStep(0.1)
        self._bta_pressed.setDecimals(2)
        self._bta_pressed.setValue(1.0)
        self._bta_pressed.setStyleSheet(ss)
        lbl_prs = QLabel("押した時の値:")
        self._trn_layout.addRow(lbl_prs, self._bta_pressed)

        self._transform_widgets["button_to_axis"] = [
            lbl_rel, self._bta_released, lbl_prs, self._bta_pressed,
        ]

        # --- buttons_to_axis ---
        self._b2a_mode = QComboBox()
        self._b2a_mode.addItems(["direct", "ramp"])
        self._b2a_mode.setStyleSheet(self._combo_style())
        lbl_b2a_mode = QLabel("モード:")
        self._trn_layout.addRow(lbl_b2a_mode, self._b2a_mode)

        self._b2a_speed = QDoubleSpinBox()
        self._b2a_speed.setRange(0.1, 10.0)
        self._b2a_speed.setSingleStep(0.1)
        self._b2a_speed.setDecimals(2)
        self._b2a_speed.setValue(1.0)
        self._b2a_speed.setStyleSheet(ss)
        lbl_spd = QLabel("速度 (/秒):")
        self._trn_layout.addRow(lbl_spd, self._b2a_speed)

        self._b2a_center = QCheckBox()
        self._b2a_center.setStyleSheet("QCheckBox { color: #e0e0e0; }")
        lbl_ctr = QLabel("中央復帰:")
        self._trn_layout.addRow(lbl_ctr, self._b2a_center)

        self._transform_widgets["buttons_to_axis"] = [
            lbl_b2a_mode, self._b2a_mode, lbl_spd, self._b2a_speed,
            lbl_ctr, self._b2a_center,
        ]

        # 初期表示: すべて非表示
        for widgets in self._transform_widgets.values():
            for w in widgets:
                w.setVisible(False)

    def _on_transform_type_changed(self, index: int) -> None:
        """変換タイプのドロップダウン変更時にパラメータフィールドを切り替える."""
        selected_internal = self._trn_type.currentData()

        # すべて非表示
        all_widgets: set[int] = set()
        for widgets in self._transform_widgets.values():
            for w in widgets:
                w.setVisible(False)
                all_widgets.add(id(w))

        # 選択された変換のウィジェットだけ表示
        if selected_internal in self._transform_widgets:
            for w in self._transform_widgets[selected_internal]:
                w.setVisible(True)

        # 説明を更新
        desc = ""
        for _, internal, d in _TRANSFORM_TYPES:
            if internal == selected_internal:
                desc = d
                break
        self._trn_desc.setText(desc)
        self._sync_output_controls_for_transform(selected_internal)
        self._sync_input_controls_for_transform(selected_internal)

    def _sync_input_controls_for_transform(self, transform_type: str) -> None:
        """変換タイプに応じて入力タイプを切り替える."""
        input_type, _ = _forced_io_types_for_transform(transform_type)
        if input_type is not None:
            self._inp_type.setCurrentText(input_type)
        elif (
            transform_type in ("button_to_axis", "button_split")
            and self._inp_type.currentText() not in ("button", "hat")
        ):
            self._inp_type.setCurrentText("button")

    def _sync_output_controls_for_transform(self, transform_type: str) -> None:
        """変換タイプに応じて出力欄の表示を切り替える."""
        _, output_type = _forced_io_types_for_transform(transform_type)
        is_button_split = transform_type == "button_split"
        is_axis_dual = transform_type == "axis_to_dual_button"
        has_secondary_button = is_button_split or is_axis_dual
        was_secondary_visible = self._out_off_index.isVisible()

        if is_button_split:
            self._out_index_label.setText("ONインデックス:")
            self._out_off_index_label.setText("OFFインデックス:")
        elif is_axis_dual:
            self._out_index_label.setText("-方向インデックス:")
            self._out_off_index_label.setText("+方向インデックス:")
        else:
            self._out_index_label.setText("インデックス:")

        self._out_off_index_label.setVisible(has_secondary_button)
        self._out_off_index.setVisible(has_secondary_button)

        if output_type is not None:
            self._out_type.setCurrentText(output_type)
            self._out_type.setEnabled(False)
        else:
            self._out_type.setEnabled(True)

        if has_secondary_button:
            if not was_secondary_visible and not self._populating:
                self._out_off_index.setValue(min(self._out_index.value() + 1, 127))

    def _on_output_index_changed(self, value: int) -> None:
        """2ボタン出力の副側インデックスを、未手動変更なら主側の次へ追従させる."""
        if self._trn_type.currentData() in ("button_split", "axis_to_dual_button"):
            expected_previous = min(self._last_out_index + 1, 127)
            if self._out_off_index.value() == expected_previous:
                self._out_off_index.setValue(min(value + 1, 127))
        self._last_out_index = value

    def _make_learn_button(
        self,
        target: QSpinBox,
        target_name: str,
        input_type: str | None,
    ) -> QPushButton:
        """実機ボタン検出用の小さなアクションボタンを作る."""
        button = QPushButton("検出")
        button.setFixedWidth(72)
        button.setStyleSheet(_LEARN_BTN_STYLE)
        button.setToolTip(f"{target_name}を実機操作から設定")
        button.clicked.connect(
            lambda: self._start_input_learn(target, target_name, button, input_type)
        )
        return button

    def _button_snapshot(self) -> dict[str, set[int]]:
        """現在押されているボタンの集合を取得する."""
        if self._input_backend is None:
            return {}
        states = self._input_backend.poll()
        return {
            device_id: {idx for idx, pressed in state.buttons.items() if pressed}
            for device_id, state in states.items()
        }

    def _axis_snapshot(self) -> dict[str, dict[int, float]]:
        """現在の軸値を取得する."""
        if self._input_backend is None:
            return {}
        states = self._input_backend.poll()
        return {
            device_id: dict(state.axes)
            for device_id, state in states.items()
        }

    def _hat_snapshot(self) -> dict[str, dict[int, tuple[int, int]]]:
        """現在の Hat 値を取得する."""
        if self._input_backend is None:
            return {}
        states = self._input_backend.poll()
        return {
            device_id: dict(state.hats)
            for device_id, state in states.items()
        }

    def _snapshot_for_input_type(self, input_type: str) -> object:
        if input_type == "axis":
            return self._axis_snapshot()
        if input_type == "hat":
            return self._hat_snapshot()
        return self._button_snapshot()

    def _select_input_device(self, device_id: str) -> None:
        index = self._inp_device.findData(device_id)
        if index < 0:
            dev = next((d for d in self._detected_devices if d.device_id == device_id), None)
            label = f"{dev.name} ({device_id})" if dev is not None and dev.name else device_id
            self._inp_device.addItem(label, device_id)
            index = self._inp_device.count() - 1
        self._inp_device.setCurrentIndex(index)

    def _start_input_learn(
        self,
        target: QSpinBox,
        target_name: str,
        button: QPushButton,
        input_type: str | None,
    ) -> None:
        """次に操作された入力を入力デバイスとインデックスへ反映する."""
        if self._input_backend is None:
            QMessageBox.warning(self, "入力検出", "入力バックエンドが初期化されていません。")
            return
        if self._learn_timer.isActive():
            self._learn_timer.stop()
        detect_type = input_type or self._inp_type.currentText()
        self._learn_target = target
        self._learn_button = button
        self._learn_target_name = target_name
        self._learn_input_type = detect_type
        self._learn_baseline = self._snapshot_for_input_type(detect_type)
        self._learn_status.setText(f"{target_name}: 入力待ち")
        self._learn_status.setVisible(True)
        self._set_button_learn_enabled(False)
        self._learn_timer.start()

    def _poll_button_learn(self) -> None:
        detected = self._detect_input_change()
        if detected is None:
            return

        device_id, input_index, value = detected
        if self._learn_target is not None:
            self._select_input_device(device_id)
            self._learn_target.setValue(input_index)
            if self._learn_input_type == "hat":
                self._set_hat_direction(value)
            display_name = _input_device_display_name(device_id, self._detected_devices)
            self._learn_status.setText(self._learn_result_text(display_name, input_index, value))
            self._learn_status.setVisible(True)
        self._stop_button_learn()

    def _detect_input_change(self) -> tuple[str, int, object] | None:
        if self._learn_input_type == "axis":
            current_axis = self._axis_snapshot()
            detected_axis = _newly_moved_axis(
                self._learn_baseline,  # type: ignore[arg-type]
                current_axis,
            )
            self._learn_baseline = current_axis
            if detected_axis is None:
                return None
            device_id, axis_index, value = detected_axis
            return device_id, axis_index, value

        if self._learn_input_type == "hat":
            current_hat = self._hat_snapshot()
            detected_hat = _newly_moved_hat(
                self._learn_baseline,  # type: ignore[arg-type]
                current_hat,
            )
            self._learn_baseline = current_hat
            if detected_hat is None:
                return None
            device_id, hat_index, value = detected_hat
            return device_id, hat_index, value

        current_buttons = self._button_snapshot()
        detected_button = _newly_pressed_button(
            self._learn_baseline,  # type: ignore[arg-type]
            current_buttons,
        )
        self._learn_baseline = current_buttons
        if detected_button is None:
            return None
        device_id, button_index = detected_button
        return device_id, button_index, True

    def _set_hat_direction(self, value: object) -> None:
        if not isinstance(value, tuple) or len(value) != 2:
            return
        index = self._hat_direction.findData(value)
        if index < 0:
            label = f"({value[0]}, {value[1]})"
            self._hat_direction.addItem(label, value)
            index = self._hat_direction.count() - 1
        self._hat_direction.setCurrentIndex(index)

    def _learn_result_text(self, display_name: str, input_index: int, value: object) -> str:
        prefix = f"{self._learn_target_name}: {display_name}"
        if self._learn_input_type == "axis":
            return f"{prefix} / Axis {input_index} ({float(value):+.3f})"
        if self._learn_input_type == "hat":
            return f"{prefix} / Hat {input_index} {value}"
        return f"{prefix} / B{input_index}"

    def _stop_button_learn(self) -> None:
        self._learn_timer.stop()
        self._set_button_learn_enabled(True)
        self._learn_target = None
        self._learn_button = None
        self._learn_target_name = ""
        self._learn_input_type = ""
        self._learn_baseline = {}

    def _set_button_learn_enabled(self, enabled: bool) -> None:
        for button in (self._btn_learn_index, self._btn_learn_neg, self._btn_learn_pos):
            is_active = button is self._learn_button
            button.setEnabled(enabled or is_active)
            button.setText("待機中" if is_active and not enabled else "検出")
            button.setStyleSheet(
                _LEARN_BTN_ACTIVE_STYLE
                if is_active and not enabled
                else _LEARN_BTN_STYLE
            )

    def _on_input_type_changed(self, text: str) -> None:
        """入力タイプ変更時に button_pair 用フィールドの表示を切り替える."""
        is_pair = text == "button_pair"
        is_single_input = text in ("axis", "button", "hat")
        is_hat = text == "hat"
        show_index = not is_pair
        self._inp_index_label.setVisible(show_index)
        self._inp_index.setVisible(show_index)
        self._btn_learn_index.setVisible(is_single_input)
        self._inp_neg_label.setVisible(is_pair)
        self._inp_neg_index.setVisible(is_pair)
        self._btn_learn_neg.setVisible(is_pair)
        self._inp_pos_label.setVisible(is_pair)
        self._inp_pos_index.setVisible(is_pair)
        self._btn_learn_pos.setVisible(is_pair)
        self._hat_direction_label.setVisible(is_hat)
        self._hat_direction.setVisible(is_hat)

    def _populate(self) -> None:
        """既存ルールの値をUIに反映する."""
        self._populating = True
        r = self._rule
        self._name_edit.setText(r.name)

        # モード
        mode_text = r.mode if r.mode != "*" else "* (全モード共通)"
        idx = self._mode_combo.findData(r.mode)
        if idx >= 0:
            self._mode_combo.setCurrentIndex(idx)
        else:
            self._mode_combo.setCurrentText(mode_text)

        # 入力デバイス
        dev_idx = self._inp_device.findData(r.input.device)
        if dev_idx < 0:
            dev_idx = self._inp_device.findText(r.input.device)
        if dev_idx >= 0:
            self._inp_device.setCurrentIndex(dev_idx)
        else:
            self._inp_device.setCurrentText(r.input.device)

        self._inp_type.setCurrentText(r.input.type)
        self._inp_index.setValue(r.input.index)
        if r.input.negative_index is not None:
            self._inp_neg_index.setValue(r.input.negative_index)
        if r.input.positive_index is not None:
            self._inp_pos_index.setValue(r.input.positive_index)
        hat_direction = (r.input.hat_x, r.input.hat_y)
        hat_idx = self._hat_direction.findData(hat_direction)
        if hat_idx >= 0:
            self._hat_direction.setCurrentIndex(hat_idx)
        self._on_input_type_changed(r.input.type)

        # 出力
        self._out_type.setCurrentText(r.output.type)
        self._out_index.setValue(r.output.index)
        self._last_out_index = r.output.index
        self._out_name.setText(r.output.name)

        # フィルタ
        self._debounce.setValue(r.filters.debounce_ms)
        self._deadzone.setValue(r.filters.deadzone)
        self._curve.setValue(r.filters.curve)
        self._invert.setChecked(r.filters.invert)
        self._smoothing.setValue(r.filters.smoothing)
        self._toggle.setChecked(r.filters.toggle)

        # 変換タイプ
        t = r.transform
        trn_internal = t.type
        trn_idx = self._trn_type.findData(trn_internal)
        if trn_idx >= 0:
            self._trn_type.setCurrentIndex(trn_idx)
        else:
            self._trn_type.setCurrentIndex(0)  # パススルー

        # 変換パラメータ
        self._atb_on_th.setValue(t.on_threshold)
        self._atb_off_th.setValue(t.off_threshold)

        self._dual_neg_on.setValue(float(t.negative.get("on_threshold", -0.60)))
        self._dual_neg_off.setValue(float(t.negative.get("off_threshold", -0.45)))
        self._dual_pos_on.setValue(float(t.positive.get("on_threshold", 0.60)))
        self._dual_pos_off.setValue(float(t.positive.get("off_threshold", 0.45)))

        self._bta_released.setValue(t.released_value)
        self._bta_pressed.setValue(t.pressed_value)

        self._b2a_mode.setCurrentText(t.mode)
        self._b2a_speed.setValue(t.speed_per_sec)
        self._b2a_center.setChecked(t.return_to_center)

        if trn_internal == "axis_to_dual_button":
            self._out_off_index.setValue(
                r.output.positive_index
                if r.output.positive_index is not None
                else r.output.index + 1
            )
        else:
            self._out_off_index.setValue(t.off_button)

        self._on_transform_type_changed(self._trn_type.currentIndex())
        self._populating = False

    def get_rule(self) -> RuleConfig:
        """UIの値から RuleConfig を作成して返す."""
        # モード
        mode_data = self._mode_combo.currentData()
        if mode_data:
            mode = mode_data
        else:
            mode = self._mode_combo.currentText().strip() or "*"

        # 入力
        inp_type = self._inp_type.currentText()
        neg_idx = self._inp_neg_index.value() if inp_type == "button_pair" else None
        pos_idx = self._inp_pos_index.value() if inp_type == "button_pair" else None
        hat_direction = self._hat_direction.currentData()
        if not isinstance(hat_direction, tuple) or len(hat_direction) != 2:
            hat_direction = (0, 1)

        # 変換
        trn_internal = self._trn_type.currentData() or ""
        transform = self._build_transform_config(trn_internal)
        input_device_text = self._inp_device.currentText().strip()
        input_device_index = self._inp_device.findText(input_device_text)
        if input_device_index >= 0:
            input_device_data = self._inp_device.itemData(input_device_index)
            input_device = (
                str(input_device_data)
                if input_device_data is not None
                else input_device_text
            )
        else:
            input_device = input_device_text

        return RuleConfig(
            name=self._name_edit.text().strip(),
            mode=mode,
            input=InputConfig(
                device=input_device,
                type=inp_type,
                index=self._inp_index.value(),
                negative_index=neg_idx,
                positive_index=pos_idx,
                hat_x=int(hat_direction[0]),
                hat_y=int(hat_direction[1]),
            ),
            filters=FiltersConfig(
                debounce_ms=self._debounce.value(),
                deadzone=self._deadzone.value(),
                curve=self._curve.value(),
                invert=self._invert.isChecked(),
                smoothing=self._smoothing.value(),
                toggle=self._toggle.isChecked(),
            ),
            transform=transform,
            output=RuleOutputConfig(
                type=self._out_type.currentText(),
                index=self._out_index.value(),
                positive_index=(
                    self._out_off_index.value()
                    if trn_internal == "axis_to_dual_button"
                    else None
                ),
                name=self._out_name.text().strip(),
            ),
        )

    def _build_transform_config(self, trn_type: str) -> TransformConfig:
        """選択された変換タイプに応じた TransformConfig を構築する."""
        if trn_type == "axis_to_button":
            return TransformConfig(
                type="axis_to_button",
                on_threshold=self._atb_on_th.value(),
                off_threshold=self._atb_off_th.value(),
            )
        elif trn_type == "axis_negative_to_button":
            return TransformConfig(
                type="axis_negative_to_button",
                on_threshold=self._atb_on_th.value(),
                off_threshold=self._atb_off_th.value(),
                negative_direction=True,
            )
        elif trn_type == "axis_to_dual_button":
            return TransformConfig(
                type="axis_to_dual_button",
                negative={
                    "on_threshold": self._dual_neg_on.value(),
                    "off_threshold": self._dual_neg_off.value(),
                },
                positive={
                    "on_threshold": self._dual_pos_on.value(),
                    "off_threshold": self._dual_pos_off.value(),
                },
            )
        elif trn_type == "button_to_axis":
            return TransformConfig(
                type="button_to_axis",
                released_value=self._bta_released.value(),
                pressed_value=self._bta_pressed.value(),
            )
        elif trn_type == "buttons_to_axis":
            return TransformConfig(
                type="buttons_to_axis",
                mode=self._b2a_mode.currentText(),
                speed_per_sec=self._b2a_speed.value(),
                return_to_center=self._b2a_center.isChecked(),
            )
        elif trn_type == "button_split":
            return TransformConfig(
                type="button_split",
                on_button=self._out_index.value(),
                off_button=self._out_off_index.value(),
            )
        else:
            # パススルー
            return TransformConfig()

    def accept(self) -> None:
        """必須項目が空のルールを保存しない."""
        errors = _validate_rule_for_edit(self.get_rule())
        if errors:
            QMessageBox.warning(
                self,
                "入力エラー",
                "以下を修正してください:\n\n- " + "\n- ".join(errors),
            )
            return
        super().accept()


class MappingEditor(QWidget):
    """マッピングルール一覧パネル.

    Signals:
        profile_changed: プロファイルが編集されたとき通知する.
    """

    profile_changed: Signal = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._profile: ProfileConfig | None = None
        self._profile_path: str | None = None
        self._detected_devices: list[DeviceInfo] = []
        self._input_backend: InputBackend | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # ヘッダ
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
        self._table.doubleClicked.connect(self._on_edit_rule)
        layout.addWidget(self._table)

        # ボタン行
        btn_row = QHBoxLayout()

        self._btn_add = QPushButton("＋ 追加")
        self._btn_add.setStyleSheet(
            _BTN_STYLE + "QPushButton { background: #065f46; color: white; }"
            "QPushButton:hover { background: #047857; }"
        )
        self._btn_add.clicked.connect(self._on_add_rule)
        btn_row.addWidget(self._btn_add)

        self._btn_edit = QPushButton("✏ 編集")
        self._btn_edit.setStyleSheet(
            _BTN_STYLE + "QPushButton { background: #1e40af; color: white; }"
            "QPushButton:hover { background: #2563eb; }"
        )
        self._btn_edit.clicked.connect(self._on_edit_rule)
        btn_row.addWidget(self._btn_edit)

        self._btn_delete = QPushButton("🗑 削除")
        self._btn_delete.setStyleSheet(
            _BTN_STYLE + "QPushButton { background: #7f1d1d; color: white; }"
            "QPushButton:hover { background: #991b1b; }"
        )
        self._btn_delete.clicked.connect(self._on_delete_rule)
        btn_row.addWidget(self._btn_delete)

        btn_row.addStretch()

        self._btn_save = QPushButton("💾 保存")
        self._btn_save.setStyleSheet(
            _BTN_STYLE + "QPushButton { background: #78350f; color: white; }"
            "QPushButton:hover { background: #92400e; }"
        )
        self._btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self._btn_save)

        self._btn_save_as = QPushButton("📄 別名保存")
        self._btn_save_as.setStyleSheet(
            _BTN_STYLE + "QPushButton { background: #78350f; color: white; }"
            "QPushButton:hover { background: #92400e; }"
        )
        self._btn_save_as.clicked.connect(self._on_save_as)
        btn_row.addWidget(self._btn_save_as)

        layout.addLayout(btn_row)

    def load_profile(self, profile: ProfileConfig, path: str | None = None) -> None:
        """プロファイルを読み込んでテーブルを更新する."""
        self._profile = profile
        self._profile_path = path
        self._profile_label.setText(f"プロファイル: {profile.name} v{profile.version}")
        self._refresh_table()

    def set_detected_devices(self, devices: list[DeviceInfo]) -> None:
        """入力バックエンドが検出した実デバイス一覧を保持する."""
        self._detected_devices = list(devices)

    def set_input_backend(self, backend: InputBackend) -> None:
        """ボタン検出に使う入力バックエンドを保持する."""
        self._input_backend = backend

    def _get_device_names(self) -> list[str]:
        """プロファイルからデバイス論理名一覧を取得する."""
        if self._profile is None:
            return []
        return list(self._profile.devices.keys())

    def _get_mode_names(self) -> list[str]:
        """プロファイルからモード名一覧を取得する."""
        if self._profile is None:
            return []
        return list(self._profile.modes.definitions)

    def _transform_display_name(self, internal: str) -> str:
        """変換タイプの内部名を表示名に変換する."""
        for display, internal_name, _ in _TRANSFORM_TYPES:
            if internal_name == internal:
                return display
        return internal or "passthrough"

    def _refresh_table(self) -> None:
        if self._profile is None:
            return
        rules = self._profile.rules
        self._table.setRowCount(len(rules))
        for row, rule in enumerate(rules):
            self._table.setItem(row, 0, QTableWidgetItem(rule.name))
            self._table.setItem(row, 1, QTableWidgetItem(rule.mode))
            input_device_text = _input_device_display_name(
                rule.input.device,
                self._detected_devices,
            )
            input_device_item = QTableWidgetItem(input_device_text)
            if input_device_text != rule.input.device:
                input_device_item.setToolTip(rule.input.device)
            self._table.setItem(row, 2, input_device_item)
            if rule.input.type == "button_pair":
                neg_idx = (
                    rule.input.negative_index
                    if rule.input.negative_index is not None
                    else rule.input.index
                )
                pos_idx = (
                    rule.input.positive_index
                    if rule.input.positive_index is not None
                    else rule.input.index + 1
                )
                input_desc = f"{rule.input.type}[-:{neg_idx}, +:{pos_idx}]"
            elif rule.input.type == "hat":
                input_desc = (
                    f"{rule.input.type}[{rule.input.index}]"
                    f"({rule.input.hat_x}, {rule.input.hat_y})"
                )
            else:
                input_desc = f"{rule.input.type}[{rule.input.index}]"
            self._table.setItem(row, 3, QTableWidgetItem(input_desc))
            trn_desc = self._transform_display_name(rule.transform.type)
            self._table.setItem(row, 4, QTableWidgetItem(trn_desc))
            if rule.transform.type == "axis_to_dual_button":
                pos_idx = (
                    rule.output.positive_index
                    if rule.output.positive_index is not None
                    else rule.output.index + 1
                )
                out_desc = f"{rule.output.type}[-:{rule.output.index}, +:{pos_idx}]"
            elif rule.transform.type == "button_split":
                out_desc = (
                    f"{rule.output.type}[ON:{rule.output.index}, "
                    f"OFF:{rule.transform.off_button}]"
                )
            else:
                out_desc = f"{rule.output.type}[{rule.output.name or rule.output.index}]"
            self._table.setItem(row, 5, QTableWidgetItem(out_desc))
            filter_parts = []
            if rule.filters.debounce_ms > 0:
                filter_parts.append(f"db={rule.filters.debounce_ms}ms")
            if rule.filters.deadzone > 0:
                filter_parts.append(f"dz={rule.filters.deadzone:.2f}")
            if rule.filters.curve != 1.0:
                filter_parts.append(f"crv={rule.filters.curve:.1f}")
            if rule.filters.invert:
                filter_parts.append("inv")
            if rule.filters.smoothing > 0:
                filter_parts.append(f"sm={rule.filters.smoothing:.2f}")
            if rule.filters.toggle:
                filter_parts.append("tgl")
            self._table.setItem(row, 6, QTableWidgetItem(", ".join(filter_parts) or "-"))

    def _selected_row(self) -> int | None:
        """選択中の行インデックスを返す."""
        rows = self._table.selectionModel().selectedRows()
        if rows:
            return rows[0].row()
        return None

    def _open_dialog(self, rule: RuleConfig | None = None) -> RuleEditDialog:
        """デバイス名・モード名を渡してダイアログを作成する."""
        return RuleEditDialog(
            rule=rule,
            device_names=self._get_device_names(),
            detected_devices=self._detected_devices,
            input_backend=self._input_backend,
            mode_names=self._get_mode_names(),
            parent=self,
        )

    def _on_add_rule(self) -> None:
        """ルール追加ダイアログを表示する."""
        if self._profile is None:
            QMessageBox.information(self, "情報", "先にプロファイルを読み込んでください。")
            return
        dlg = self._open_dialog()
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_rule = dlg.get_rule()
            if not new_rule.name:
                QMessageBox.warning(self, "入力エラー", "ルール名は必須です。")
                return
            self._profile.rules.append(new_rule)
            self._refresh_table()
            self.profile_changed.emit()
            logger.info("ルール追加: %s", new_rule.name)

    def _on_edit_rule(self) -> None:
        """選択中のルールを編集する."""
        if self._profile is None:
            return
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "情報", "編集するルールを選択してください。")
            return
        rule = self._profile.rules[row]
        dlg = self._open_dialog(rule=rule)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            updated = dlg.get_rule()
            if not updated.name:
                QMessageBox.warning(self, "入力エラー", "ルール名は必須です。")
                return
            self._profile.rules[row] = updated
            self._refresh_table()
            self.profile_changed.emit()
            logger.info("ルール編集: %s", updated.name)

    def _on_delete_rule(self) -> None:
        """選択中のルールを削除する."""
        if self._profile is None:
            return
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "情報", "削除するルールを選択してください。")
            return
        rule = self._profile.rules[row]
        reply = QMessageBox.question(
            self, "確認",
            f"ルール '{rule.name}' を削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            del self._profile.rules[row]
            self._refresh_table()
            self.profile_changed.emit()
            logger.info("ルール削除: %s", rule.name)

    def _on_save(self) -> None:
        """現在のプロファイルを上書き保存する."""
        if self._profile is None:
            QMessageBox.information(self, "情報", "保存するプロファイルがありません。")
            return
        if not self._profile_path:
            self._on_save_as()
            return
        try:
            save_profile(self._profile, self._profile_path)
            QMessageBox.information(self, "保存完了", f"保存しました:\n{self._profile_path}")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"保存に失敗しました:\n{e}")

    def _on_save_as(self) -> None:
        """別名でプロファイルを保存する."""
        if self._profile is None:
            QMessageBox.information(self, "情報", "保存するプロファイルがありません。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "プロファイルを保存",
            str(Path.cwd()),
            "YAML Files (*.yaml *.yml);;All Files (*)",
        )
        if not path:
            return
        try:
            save_profile(self._profile, path)
            self._profile_path = path
            QMessageBox.information(self, "保存完了", f"保存しました:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"保存に失敗しました:\n{e}")
