"""button_split のパイプライン動作テスト."""

from controller_mapper.config.schema import (
    InputConfig,
    ProfileConfig,
    RuleConfig,
    RuleOutputConfig,
    TransformConfig,
)
from controller_mapper.core.pipeline import Pipeline
from controller_mapper.core.state import DeviceState, InputState


def _button_split_pipeline(
    input_type: str = "button",
    output_index: int = 0,
    transform_on_button: int = 0,
    transform_off_button: int = 1,
) -> Pipeline:
    profile = ProfileConfig()
    profile.rules.append(
        RuleConfig(
            name="split",
            input=InputConfig(device="controller", type=input_type, index=0),
            transform=TransformConfig(
                type="button_split",
                on_button=transform_on_button,
                off_button=transform_off_button,
            ),
            output=RuleOutputConfig(type="button", index=output_index),
        )
    )
    return Pipeline(profile)


def test_button_split_writes_on_button_and_releases_off_button() -> None:
    pipeline = _button_split_pipeline()

    _, output = pipeline.process(
        InputState(devices={"controller": DeviceState(buttons={0: True})})
    )

    assert output.buttons[0] is True
    assert output.buttons[1] is False


def test_button_split_releases_on_button_and_writes_off_button() -> None:
    pipeline = _button_split_pipeline()

    _, output = pipeline.process(
        InputState(devices={"controller": DeviceState(buttons={0: False})})
    )

    assert output.buttons[0] is False
    assert output.buttons[1] is True


def test_button_split_uses_index_even_if_profile_has_button_pair_type() -> None:
    pipeline = _button_split_pipeline(input_type="button_pair")

    _, output = pipeline.process(
        InputState(devices={"controller": DeviceState(buttons={0: False})})
    )

    assert output.buttons[0] is False
    assert output.buttons[1] is True


def test_button_split_uses_output_index_for_on_button() -> None:
    pipeline = _button_split_pipeline(
        output_index=7,
        transform_on_button=99,
        transform_off_button=8,
    )

    _, output = pipeline.process(
        InputState(devices={"controller": DeviceState(buttons={0: True})})
    )

    assert output.buttons[7] is True
    assert output.buttons[8] is False
    assert 99 not in output.buttons
