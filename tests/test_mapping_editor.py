"""Mapping Editor の非GUIロジックのテスト."""

from controller_mapper.app.mapping_editor import (
    _build_input_device_choices,
    _forced_io_types_for_transform,
    _input_device_display_name,
    _newly_moved_axis,
    _newly_moved_hat,
    _newly_pressed_button,
    _validate_rule_for_edit,
)
from controller_mapper.config.schema import InputConfig, RuleConfig, RuleOutputConfig
from controller_mapper.core.state import DeviceInfo


def _dev(device_id: str, name: str = "Device") -> DeviceInfo:
    return DeviceInfo(
        device_id=device_id,
        name=name,
        num_axes=0,
        num_buttons=0,
        num_hats=0,
        backend_name="pygame",
    )


def test_input_device_choices_include_profile_and_detected_devices() -> None:
    choices = _build_input_device_choices(
        ["x56_stick"],
        [_dev("pygame_0", "X56 Stick"), _dev("pygame_1", "T-Rudder")],
    )

    assert choices == [
        ("x56_stick", "x56_stick"),
        ("X56 Stick (pygame_0)", "pygame_0"),
        ("T-Rudder (pygame_1)", "pygame_1"),
    ]


def test_input_device_choices_skip_duplicate_values() -> None:
    choices = _build_input_device_choices(
        ["pygame_0"],
        [_dev("pygame_0", "X56 Stick"), _dev("pygame_1", "T-Rudder")],
    )

    assert choices == [
        ("pygame_0", "pygame_0"),
        ("T-Rudder (pygame_1)", "pygame_1"),
    ]


def test_input_device_display_name_uses_detected_device_name() -> None:
    display = _input_device_display_name(
        "pygame_0",
        [_dev("pygame_0", "X56 Stick")],
    )

    assert display == "X56 Stick"


def test_input_device_display_name_falls_back_to_id() -> None:
    display = _input_device_display_name(
        "x56_stick",
        [_dev("pygame_0", "X56 Stick")],
    )

    assert display == "x56_stick"


def test_buttons_to_axis_forces_button_pair_input_and_axis_output() -> None:
    assert _forced_io_types_for_transform("buttons_to_axis") == ("button_pair", "axis")


def test_button_split_forces_only_button_output() -> None:
    assert _forced_io_types_for_transform("button_split") == (None, "button")


def test_newly_pressed_button_returns_first_new_button() -> None:
    detected = _newly_pressed_button(
        {"pygame_0": {1}, "pygame_1": {2}},
        {"pygame_0": {1, 3}, "pygame_1": {2, 4}},
    )

    assert detected == ("pygame_0", 3)


def test_newly_pressed_button_returns_none_without_new_press() -> None:
    detected = _newly_pressed_button(
        {"pygame_0": {1}, "pygame_1": set()},
        {"pygame_0": {1}, "pygame_1": set()},
    )

    assert detected is None


def test_newly_moved_axis_returns_changed_axis() -> None:
    detected = _newly_moved_axis(
        {"pygame_0": {0: 0.0, 1: 0.1}},
        {"pygame_0": {0: 0.1, 1: 0.6}},
    )

    assert detected == ("pygame_0", 1, 0.6)


def test_newly_moved_hat_returns_non_neutral_direction() -> None:
    detected = _newly_moved_hat(
        {"pygame_0": {0: (0, 0)}},
        {"pygame_0": {0: (1, 0)}},
    )

    assert detected == ("pygame_0", 0, (1, 0))


def test_rule_edit_validation_rejects_empty_required_fields() -> None:
    errors = _validate_rule_for_edit(
        RuleConfig(
            name="",
            input=InputConfig(device="", type="axis", index=0),
            output=RuleOutputConfig(type="axis", name=""),
        )
    )

    assert errors == [
        "ルール名を入力してください。",
        "入力デバイスを選択または入力してください。",
        "軸出力では軸名を入力してください。",
    ]


def test_rule_edit_validation_accepts_button_rule() -> None:
    errors = _validate_rule_for_edit(
        RuleConfig(
            name="fire",
            input=InputConfig(device="pygame_0", type="button", index=0),
            output=RuleOutputConfig(type="button", index=1),
        )
    )

    assert errors == []
