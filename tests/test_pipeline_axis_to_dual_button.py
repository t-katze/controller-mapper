"""axis_to_dual_button のパイプライン動作テスト."""

from controller_mapper.config.schema import (
    InputConfig,
    ProfileConfig,
    RuleConfig,
    RuleOutputConfig,
    TransformConfig,
)
from controller_mapper.core.pipeline import Pipeline
from controller_mapper.core.state import DeviceState, InputState


def _axis_to_dual_pipeline() -> Pipeline:
    profile = ProfileConfig()
    profile.rules.append(
        RuleConfig(
            name="dual",
            input=InputConfig(device="controller", type="axis", index=0),
            transform=TransformConfig(
                type="axis_to_dual_button",
                negative={"on_threshold": -0.6, "off_threshold": -0.45},
                positive={"on_threshold": 0.6, "off_threshold": 0.45},
            ),
            output=RuleOutputConfig(type="button", index=7, positive_index=8),
        )
    )
    return Pipeline(profile)


def test_axis_to_dual_uses_output_index_for_negative_button() -> None:
    pipeline = _axis_to_dual_pipeline()

    _, output = pipeline.process(
        InputState(devices={"controller": DeviceState(axes={0: -0.8})})
    )

    assert output.buttons[7] is True
    assert output.buttons[8] is False


def test_axis_to_dual_uses_positive_index_for_positive_button() -> None:
    pipeline = _axis_to_dual_pipeline()

    _, output = pipeline.process(
        InputState(devices={"controller": DeviceState(axes={0: 0.8})})
    )

    assert output.buttons[7] is False
    assert output.buttons[8] is True
