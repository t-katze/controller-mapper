"""変換モジュール公開API.

設計書 §5 に対応する変換クラス群.
"""
from controller_mapper.transforms.axis_to_axis import AxisToAxisTransform
from controller_mapper.transforms.axis_to_button import (
    AxisToButtonTransform,
    AxisToDualButtonTransform,
)
from controller_mapper.transforms.button_to_axis import (
    ButtonPairToAxisTransform,
    ButtonToAxisTransform,
)
from controller_mapper.transforms.button_to_button import ButtonSplitTransform, ButtonToButtonTransform
from controller_mapper.transforms.mode_switch import ModeManager

__all__ = [
    "AxisToAxisTransform",
    "AxisToButtonTransform",
    "AxisToDualButtonTransform",
    "ButtonPairToAxisTransform",
    "ButtonSplitTransform",
    "ButtonToAxisTransform",
    "ButtonToButtonTransform",
    "ModeManager",
]
