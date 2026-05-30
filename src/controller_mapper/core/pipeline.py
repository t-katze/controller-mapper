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
from controller_mapper.transforms.button_to_button import ButtonToButtonTransform
from controller_mapper.transforms.mode_switch import ModeManager

logger = logging.getLogger(__name__)


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

        if r.input.type == "axis" and r.output.type == "axis":
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
                self._transform = AxisToButtonTransform(
                    on_threshold=t.on_threshold,
                    off_threshold=t.off_threshold,
                )
        elif r.input.type == "button" and r.output.type == "axis":
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
            # button → button
            self._transform = ButtonToButtonTransform(
                debounce_ms=f.debounce_ms,
                minimum_on_ms=f.minimum_on_ms,
                minimum_off_ms=f.minimum_off_ms,
                toggle=f.toggle,
            )

    def process(
        self,
        raw_state: InputState,
        output: OutputState,
        now: float,
        device_aliases: dict[str, str] | None = None,
    ) -> None:
        """ルールを適用してOutputStateを更新する."""
        r = self.rule
        input_device = r.input.device
        if device_aliases is not None:
            input_device = device_aliases.get(input_device, input_device)
        device_state = raw_state.devices.get(input_device)
        if device_state is None:
            return

        inp_type = r.input.type
        out_type = r.output.type

        if inp_type == "axis" and out_type == "axis":
            raw_val = device_state.axes.get(r.input.index, 0.0)
            result = self._transform.process(raw_val)
            out_name = r.output.name or "x"
            output.axes[out_name] = result

        elif inp_type == "axis" and out_type == "button":
            raw_val = device_state.axes.get(r.input.index, 0.0)
            if isinstance(self._transform, AxisToDualButtonTransform):
                neg_btn, pos_btn = self._transform.process(raw_val)
                neg_idx = self.rule.transform.negative.get("output_button", r.output.index)
                pos_idx = self.rule.transform.positive.get("output_button", r.output.index + 1)
                output.buttons[int(neg_idx)] = neg_btn
                output.buttons[int(pos_idx)] = pos_btn
            else:
                result = self._transform.process(raw_val)
                output.buttons[r.output.index] = result

        elif inp_type == "button" and out_type == "axis":
            raw_val = device_state.buttons.get(r.input.index, False)
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
            # button → button
            raw_val = device_state.buttons.get(r.input.index, False)
            result = self._transform.process(raw_val, now)
            output.buttons[r.output.index] = result


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

    def process(self, raw: InputState) -> tuple[FilteredState, OutputState]:
        """生入力を変換してFilteredStateとOutputStateを返す."""
        now = time.monotonic()
        output = OutputState()

        current_mode = self._mode_manager.current if self._mode_manager else "*"

        for rp in self._rules:
            # モードフィルタ
            if self._mode_manager and not self._mode_manager.matches(rp.rule.mode):
                continue
            try:
                rp.process(raw, output, now, self._device_aliases)
            except Exception as e:
                logger.error("ルール '%s' 処理エラー: %s", rp.rule.name, e)

        # FilteredState は今はraw_stateをコピーするだけ (将来的に軸フィルタ結果を入れる)
        filtered = FilteredState(
            timestamp=raw.timestamp,
            devices={k: v.copy() for k, v in raw.devices.items()},
        )
        return filtered, output
