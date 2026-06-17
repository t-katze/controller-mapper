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
    transform_gap_ms: float = 0.0,
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
                gap_ms=transform_gap_ms,
            ),
            output=RuleOutputConfig(type="button", index=output_index),
        )
    )
    return Pipeline(profile)


def _button_off_pipeline(
    input_type: str = "button",
    output_index: int = 3,
) -> Pipeline:
    profile = ProfileConfig()
    profile.rules.append(
        RuleConfig(
            name="off",
            input=InputConfig(device="controller", type=input_type, index=0),
            transform=TransformConfig(type="button_off"),
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


def test_button_split_gap_keeps_both_outputs_off(monkeypatch) -> None:
    current_time = 0.0
    monkeypatch.setattr(
        "controller_mapper.core.pipeline.time.monotonic",
        lambda: current_time,
    )
    pipeline = _button_split_pipeline(
        output_index=7,
        transform_off_button=8,
        transform_gap_ms=50.0,
    )

    filtered, output = pipeline.process(
        InputState(devices={"controller": DeviceState(buttons={0: False})})
    )
    assert filtered.devices["controller"].buttons[0] is False
    assert output.buttons[7] is False
    assert output.buttons[8] is True

    current_time = 0.100
    filtered, output = pipeline.process(
        InputState(devices={"controller": DeviceState(buttons={0: True})})
    )
    assert filtered.devices["controller"].buttons[0] is True
    assert output.buttons[7] is False
    assert output.buttons[8] is False

    current_time = 0.151
    _, output = pipeline.process(
        InputState(devices={"controller": DeviceState(buttons={0: True})})
    )
    assert output.buttons[7] is True
    assert output.buttons[8] is False


def test_button_off_writes_output_when_input_is_released() -> None:
    pipeline = _button_off_pipeline(output_index=3)

    _, output = pipeline.process(
        InputState(devices={"controller": DeviceState(buttons={0: False})})
    )

    assert output.buttons[3] is True


def test_button_off_releases_output_when_input_is_pressed() -> None:
    pipeline = _button_off_pipeline(output_index=3)

    _, output = pipeline.process(
        InputState(devices={"controller": DeviceState(buttons={0: True})})
    )

    assert output.buttons[3] is False


def test_button_off_can_use_hat_input() -> None:
    pipeline = _button_off_pipeline(input_type="hat", output_index=4)

    _, output = pipeline.process(
        InputState(devices={"controller": DeviceState(hats={0: (0, 0)})})
    )

    assert output.buttons[4] is True
