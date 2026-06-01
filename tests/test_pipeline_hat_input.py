"""hat 入力のパイプライン動作テスト."""

from controller_mapper.config.schema import (
    InputConfig,
    ProfileConfig,
    RuleConfig,
    RuleOutputConfig,
    TransformConfig,
)
from controller_mapper.core.pipeline import Pipeline
from controller_mapper.core.state import DeviceState, InputState


def test_hat_direction_maps_to_button() -> None:
    profile = ProfileConfig()
    profile.rules.append(
        RuleConfig(
            name="pov_right",
            input=InputConfig(
                device="controller",
                type="hat",
                index=0,
                hat_x=1,
                hat_y=0,
            ),
            output=RuleOutputConfig(type="button", index=4),
        )
    )
    pipeline = Pipeline(profile)

    _, output = pipeline.process(
        InputState(devices={"controller": DeviceState(hats={0: (1, 0)})})
    )

    assert output.buttons[4] is True


def test_hat_neutral_releases_button() -> None:
    profile = ProfileConfig()
    profile.rules.append(
        RuleConfig(
            name="pov_right",
            input=InputConfig(
                device="controller",
                type="hat",
                index=0,
                hat_x=1,
                hat_y=0,
            ),
            output=RuleOutputConfig(type="button", index=4),
        )
    )
    pipeline = Pipeline(profile)

    _, output = pipeline.process(
        InputState(devices={"controller": DeviceState(hats={0: (0, 0)})})
    )

    assert output.buttons[4] is False


def test_hat_direction_maps_to_axis_with_button_to_axis() -> None:
    profile = ProfileConfig()
    profile.rules.append(
        RuleConfig(
            name="pov_up_axis",
            input=InputConfig(
                device="controller",
                type="hat",
                index=0,
                hat_x=0,
                hat_y=1,
            ),
            transform=TransformConfig(
                type="button_to_axis",
                released_value=-1.0,
                pressed_value=1.0,
            ),
            output=RuleOutputConfig(type="axis", name="x"),
        )
    )
    pipeline = Pipeline(profile)

    _, output = pipeline.process(
        InputState(devices={"controller": DeviceState(hats={0: (0, 1)})})
    )

    assert output.axes["x"] == 1.0


def test_hat_direction_can_drive_button_split() -> None:
    profile = ProfileConfig()
    profile.rules.append(
        RuleConfig(
            name="pov_split",
            input=InputConfig(
                device="controller",
                type="hat",
                index=0,
                hat_x=0,
                hat_y=1,
            ),
            transform=TransformConfig(type="button_split", off_button=6),
            output=RuleOutputConfig(type="button", index=5),
        )
    )
    pipeline = Pipeline(profile)

    _, output = pipeline.process(
        InputState(devices={"controller": DeviceState(hats={0: (0, 1)})})
    )

    assert output.buttons[5] is True
    assert output.buttons[6] is False
