"""同じ出力ボタンを複数ルールで共有するパイプライン動作テスト."""

from controller_mapper.config.schema import (
    InputConfig,
    ProfileConfig,
    RuleConfig,
    RuleOutputConfig,
    TransformConfig,
)
from controller_mapper.core.pipeline import Pipeline
from controller_mapper.core.state import DeviceState, InputState


def test_shared_button_output_is_pressed_when_first_rule_is_pressed() -> None:
    profile = ProfileConfig()
    profile.rules.extend(
        [
            RuleConfig(
                name="primary",
                input=InputConfig(device="controller", type="button", index=0),
                output=RuleOutputConfig(type="button", index=4),
            ),
            RuleConfig(
                name="secondary",
                input=InputConfig(device="controller", type="button", index=1),
                output=RuleOutputConfig(type="button", index=4),
            ),
        ]
    )
    pipeline = Pipeline(profile)

    _, output = pipeline.process(
        InputState(devices={"controller": DeviceState(buttons={0: True, 1: False})})
    )

    assert output.buttons[4] is True


def test_shared_button_output_is_pressed_when_second_rule_is_pressed() -> None:
    profile = ProfileConfig()
    profile.rules.extend(
        [
            RuleConfig(
                name="primary",
                input=InputConfig(device="controller", type="button", index=0),
                output=RuleOutputConfig(type="button", index=4),
            ),
            RuleConfig(
                name="secondary",
                input=InputConfig(device="controller", type="button", index=1),
                output=RuleOutputConfig(type="button", index=4),
            ),
        ]
    )
    pipeline = Pipeline(profile)

    _, output = pipeline.process(
        InputState(devices={"controller": DeviceState(buttons={0: False, 1: True})})
    )

    assert output.buttons[4] is True


def test_shared_button_output_is_released_when_all_rules_are_released() -> None:
    profile = ProfileConfig()
    profile.rules.extend(
        [
            RuleConfig(
                name="primary",
                input=InputConfig(device="controller", type="button", index=0),
                output=RuleOutputConfig(type="button", index=4),
            ),
            RuleConfig(
                name="secondary",
                input=InputConfig(device="controller", type="button", index=1),
                output=RuleOutputConfig(type="button", index=4),
            ),
        ]
    )
    pipeline = Pipeline(profile)

    _, output = pipeline.process(
        InputState(devices={"controller": DeviceState(buttons={0: False, 1: False})})
    )

    assert output.buttons[4] is False


def test_button_split_false_output_does_not_clear_shared_pressed_button() -> None:
    profile = ProfileConfig()
    profile.rules.extend(
        [
            RuleConfig(
                name="primary",
                input=InputConfig(device="controller", type="button", index=0),
                output=RuleOutputConfig(type="button", index=4),
            ),
            RuleConfig(
                name="split",
                input=InputConfig(device="controller", type="button", index=1),
                transform=TransformConfig(type="button_split", off_button=5),
                output=RuleOutputConfig(type="button", index=4),
            ),
        ]
    )
    pipeline = Pipeline(profile)

    _, output = pipeline.process(
        InputState(devices={"controller": DeviceState(buttons={0: True, 1: False})})
    )

    assert output.buttons[4] is True
    assert output.buttons[5] is True
