"""YAMLプロファイルのスキーマ定義.

設計書 §11 に対応.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class DeviceMatchConfig:
    name_contains: str = ""
    role: str = ""


@dataclass
class DeviceConfig:
    match: DeviceMatchConfig = field(default_factory=DeviceMatchConfig)


@dataclass
class OutputConfig:
    type: str = "null"         # "vjoy" | "null"
    device_id: int = 1


@dataclass
class GlobalConfig:
    update_rate_hz: int = 500
    gui_rate_hz: int = 30


@dataclass
class ModesConfig:
    default: str = "default"
    definitions: list[str] = field(default_factory=lambda: ["default"])


@dataclass
class InputConfig:
    device: str = ""
    type: str = "button"       # "button" | "axis" | "button_pair" | "hat"
    index: int = 0
    negative_index: int | None = None
    positive_index: int | None = None
    hat_x: int = 0
    hat_y: int = 1


@dataclass
class FiltersConfig:
    debounce_ms: float = 0.0
    minimum_on_ms: float = 0.0
    minimum_off_ms: float = 0.0
    deadzone: float = 0.0
    end_deadzone: float = 0.0
    curve: float = 1.0
    invert: bool = False
    smoothing: float = 0.0
    toggle: bool = False


@dataclass
class TransformConfig:
    type: str = ""                  # "axis_to_button" | "axis_to_dual_button" |
                                    # "button_to_axis" | "buttons_to_axis" |
                                    # "axis_negative_to_button" | "button_split"
    on_threshold: float = 0.5
    off_threshold: float = 0.4
    released_value: float = 0.0
    pressed_value: float = 1.0
    mode: str = "direct"            # "direct" | "ramp"
    speed_per_sec: float = 1.0
    return_to_center: bool = False
    negative: dict[str, Any] = field(default_factory=dict)
    positive: dict[str, Any] = field(default_factory=dict)
    # axis_negative_to_button: 軸の-方向で判定
    negative_direction: bool = False
    # button_split: ON側は output.index、OFF側は off_button に出力
    on_button: int = 0
    off_button: int = 1


@dataclass
class RuleOutputConfig:
    device: str = "vjoy1"
    type: str = "button"           # "button" | "axis"
    index: int = 0
    positive_index: int | None = None
    name: str = ""                 # 軸名 (x/y/z/rx/ry/rz/slider1/slider2)


@dataclass
class RuleConfig:
    name: str = ""
    mode: str = "*"
    input: InputConfig = field(default_factory=InputConfig)
    filters: FiltersConfig = field(default_factory=FiltersConfig)
    transform: TransformConfig = field(default_factory=TransformConfig)
    output: RuleOutputConfig = field(default_factory=RuleOutputConfig)


@dataclass
class ProfileConfig:
    name: str = "default"
    version: int = 1
    devices: dict[str, DeviceConfig] = field(default_factory=dict)
    output: OutputConfig = field(default_factory=OutputConfig)
    global_: GlobalConfig = field(default_factory=GlobalConfig)
    modes: ModesConfig = field(default_factory=ModesConfig)
    rules: list[RuleConfig] = field(default_factory=list)
