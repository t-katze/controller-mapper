"""変換パイプライン.

設計書 §3 全体構成, §9 処理周期 に対応.

Input → Filter → Mapping Engine → Output の流れを実装する.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from controller_mapper.config.schema import ProfileConfig, RuleConfig
from controller_mapper.core.state import DeviceState, FilteredState, InputState, OutputState
from controller_mapper.filters.debounce import DebounceFilter
from controller_mapper.filters.deadzone import DeadzoneFilter
from controller_mapper.filters.curve import CurveFilter
from controller_mapper.filters.smoothing import EwmaFilter
from controller_mapper.transforms.axis_to_axis import AxisToAxisTransform
from controller_mapper.transforms.axis_to_button import AxisToButtonTransform, AxisToDualButtonTransform
from controller_mapper.transforms.button_to_axis import ButtonToAxisTransform, ButtonPairToAxisTransform
from controller_mapper.transforms.button_to_button import ButtonSplitTransform, ButtonToButtonTransform
from controller_mapper.transforms.mode_switch import ModeManager

logger = logging.getLogger(__name__)


def _write_button_output(output: OutputState, index: int, pressed: bool) -> None:
    """同じ出力ボタンへ複数ルールが書く場合はOR合成する."""
    idx = int(index)
    output.buttons[idx] = output.buttons.get(idx, False) or bool(pressed)


class RuleProcessor:
    """単一ルールの変換処理を保持するクラス."""

    def __init__(self, rule: RuleConfig) -> None:
        self.rule = rule
        self._transform: Any = None
        self._build_transform()

    def _build_transform(self) -> None:
        r = self.rule
        f = r.filters
        t = r.transform

        if r.output.type == "button" and t.type == "button_split":
            # button_split: input.index のON/OFFを2つの仮想ボタンへ常時反映する
            self._transform = ButtonSplitTransform(
                on_button=r.output.index,
                off_button=t.off_button,
                debounce_ms=f.debounce_ms,
            )
        elif r.input.type == "axis" and r.output.type == "axis":
            # smoothing: alpha=1.0 でEWMA無効
            alpha = 1.0 - f.smoothing if f.smoothing > 0 else 1.0
            self._transform = AxisToAxisTransform(
                deadzone=f.deadzone,
                end_deadzone=f.end_deadzone,
                curve=f.curve,
                invert=f.invert,
                smoothing_alpha=alpha,
            )
        elif r.input.type == "axis" and r.output.type == "button":
            if t.type == "axis_to_dual_button":
                neg = t.negative
                pos = t.positive
                self._transform = AxisToDualButtonTransform(
                    neg_on=float(neg.get("on_threshold", -0.60)),
                    neg_off=float(neg.get("off_threshold", -0.45)),
                    pos_on=float(pos.get("on_threshold", 0.60)),
                    pos_off=float(pos.get("off_threshold", 0.45)),
                )
            else:
                # axis_negative_to_button か negative_direction フラグで
                # 軸の-方向を判定する
                is_negative = (
                    t.type == "axis_negative_to_button"
                    or t.negative_direction
                )
                self._transform = AxisToButtonTransform(
                    on_threshold=t.on_threshold,
                    off_threshold=t.off_threshold,
                    negative=is_negative,
                )
        elif r.input.type in ("button", "hat") and r.output.type == "axis":
            self._transform = ButtonToAxisTransform(
                released_value=t.released_value,
                pressed_value=t.pressed_value,
            )
        elif r.input.type == "button_pair" and r.output.type == "axis":
            self._transform = ButtonPairToAxisTransform(
                mode=t.mode,
                speed_per_sec=t.speed_per_sec,
                return_to_center=t.return_to_center,
            )
        else:
            # button → button (通常)
            self._transform = ButtonToButtonTransform(
                debounce_ms=f.debounce_ms,
                minimum_on_ms=f.minimum_on_ms,
                minimum_off_ms=f.minimum_off_ms,
                toggle=f.toggle,
            )

    def _read_boolean_input(self, device_state: DeviceState) -> bool:
        """button / hat 系入力を bool として読む."""
        inp = self.rule.input
        if inp.type == "hat":
            return device_state.hats.get(inp.index, (0, 0)) == (inp.hat_x, inp.hat_y)
        return device_state.buttons.get(inp.index, False)

    def process(
        self,
        raw_state: InputState,
        output: OutputState,
        filtered_devices: dict[str, DeviceState],
        now: float,
        device_aliases: dict[str, str] | None = None,
    ) -> None:
        """ルールを適用してOutputStateとFilteredStateを更新する."""
        r = self.rule
        input_device = r.input.device
        if device_aliases is not None:
            input_device = device_aliases.get(input_device, input_device)
        device_state = raw_state.devices.get(input_device)
        if device_state is None:
            return

        # FilteredState 用のデバイス取得/作成
        flt_dev = filtered_devices.get(input_device)

        inp_type = r.input.type
        out_type = r.output.type

        if out_type == "button" and isinstance(self._transform, ButtonSplitTransform):
            # button_split: ON/OFF を2つの仮想ボタンに分割
            raw_val = self._read_boolean_input(device_state)
            on_result, off_result = self._transform.process(raw_val, now)
            _write_button_output(output, self._transform.on_button, on_result)
            _write_button_output(output, self._transform.off_button, off_result)
            if flt_dev is not None:
                flt_dev.buttons[r.input.index] = on_result

        elif inp_type == "axis" and out_type == "axis":
            raw_val = device_state.axes.get(r.input.index, 0.0)
            result = self._transform.process(raw_val)
            out_name = r.output.name or "x"
            output.axes[out_name] = result
            # FilteredState に軸フィルタ結果を反映
            if flt_dev is not None:
                flt_dev.axes[r.input.index] = result

        elif inp_type == "axis" and out_type == "button":
            raw_val = device_state.axes.get(r.input.index, 0.0)
            if isinstance(self._transform, AxisToDualButtonTransform):
                neg_btn, pos_btn = self._transform.process(raw_val)
                neg_idx = r.output.index
                pos_idx = (
                    r.output.positive_index
                    if r.output.positive_index is not None
                    else r.output.index + 1
                )
                _write_button_output(output, neg_idx, neg_btn)
                _write_button_output(output, pos_idx, pos_btn)
            else:
                result = self._transform.process(raw_val)
                _write_button_output(output, r.output.index, result)

        elif inp_type in ("button", "hat") and out_type == "axis":
            raw_val = self._read_boolean_input(device_state)
            result = self._transform.process(raw_val)
            out_name = r.output.name or "x"
            output.axes[out_name] = result

        elif inp_type == "button_pair" and out_type == "axis":
            neg_idx = r.input.negative_index or 0
            pos_idx = r.input.positive_index or 0
            neg_pressed = device_state.buttons.get(neg_idx, False)
            pos_pressed = device_state.buttons.get(pos_idx, False)
            result = self._transform.process(neg_pressed, pos_pressed, now)
            out_name = r.output.name or "x"
            output.axes[out_name] = result

        else:
            # button → button (通常)
            raw_val = self._read_boolean_input(device_state)
            result = self._transform.process(raw_val, now)
            _write_button_output(output, r.output.index, result)
            # FilteredState にデバウンス結果を反映
            if flt_dev is not None:
                flt_dev.buttons[r.input.index] = result


class Pipeline:
    """Input → Filter → Map → Output パイプライン.

    Args:
        profile: 読み込み済みのプロファイル設定
    """

    def __init__(self, profile: ProfileConfig | None = None) -> None:
        self._rules: list[RuleProcessor] = []
        self._mode_manager: ModeManager | None = None
        self._device_aliases: dict[str, str] = {}
        if profile is not None:
            self.load_profile(profile)

    def load_profile(
        self,
        profile: ProfileConfig,
        device_aliases: dict[str, str] | None = None,
    ) -> None:
        """プロファイルを読み込んでルールを再構築する."""
        self._rules = [RuleProcessor(rule) for rule in profile.rules]
        self._mode_manager = ModeManager(
            definitions=profile.modes.definitions,
            default=profile.modes.default,
        )
        self.set_device_aliases(device_aliases or {})
        logger.info("パイプライン: %d ルールを読み込みました", len(self._rules))

    def set_device_aliases(self, device_aliases: dict[str, str]) -> None:
        self._device_aliases = dict(device_aliases)
        if self._device_aliases:
            logger.info("デバイス別名を設定: %s", self._device_aliases)

    @property
    def mode_manager(self) -> ModeManager | None:
        return self._mode_manager

    @property
    def rules(self) -> list[RuleProcessor]:
        """ルール一覧を返す (GUI参照用)."""
        return list(self._rules)

    def process(self, raw: InputState) -> tuple[FilteredState, OutputState]:
        """生入力を変換してFilteredStateとOutputStateを返す."""
        now = time.monotonic()
        output = OutputState()

        # FilteredState: rawをコピーした上でルール処理時にフィルタ結果を上書きする
        filtered_devices: dict[str, DeviceState] = {
            k: v.copy() for k, v in raw.devices.items()
        }

        current_mode = self._mode_manager.current if self._mode_manager else "*"

        for rp in self._rules:
            # モードフィルタ
            if self._mode_manager and not self._mode_manager.matches(rp.rule.mode):
                continue
            try:
                rp.process(raw, output, filtered_devices, now, self._device_aliases)
            except Exception as e:
                logger.error("ルール '%s' 処理エラー: %s", rp.rule.name, e)

        filtered = FilteredState(
            timestamp=raw.timestamp,
            devices=filtered_devices,
        )
        return filtered, output
