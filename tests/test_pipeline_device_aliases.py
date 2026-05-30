"""プロファイルの論理デバイス名と実入力デバイスIDの対応テスト."""

import pytest

from controller_mapper.config.schema import InputConfig, ProfileConfig, RuleConfig, RuleOutputConfig
from controller_mapper.core.pipeline import Pipeline
from controller_mapper.core.state import DeviceState, InputState


def test_pipeline_uses_device_aliases_for_rule_input() -> None:
    profile = ProfileConfig()
    profile.rules.append(
        RuleConfig(
            name="roll",
            input=InputConfig(device="joystick", type="axis", index=0),
            output=RuleOutputConfig(type="axis", name="x"),
        )
    )
    pipeline = Pipeline()
    pipeline.load_profile(profile, device_aliases={"joystick": "pygame_0"})

    raw = InputState(
        devices={
            "pygame_0": DeviceState(axes={0: 0.5}),
        }
    )

    _, output = pipeline.process(raw)

    assert output.axes["x"] == pytest.approx(0.5)


def test_pipeline_without_matching_device_produces_no_output() -> None:
    profile = ProfileConfig()
    profile.rules.append(
        RuleConfig(
            name="roll",
            input=InputConfig(device="joystick", type="axis", index=0),
            output=RuleOutputConfig(type="axis", name="x"),
        )
    )
    pipeline = Pipeline(profile)

    raw = InputState(
        devices={
            "pygame_0": DeviceState(axes={0: 0.5}),
        }
    )

    _, output = pipeline.process(raw)

    assert output.axes == {}