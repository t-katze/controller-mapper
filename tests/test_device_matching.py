"""プロファイルデバイスと実入力デバイスのマッチングテスト."""

from controller_mapper.config.schema import DeviceConfig, DeviceMatchConfig, ProfileConfig
from controller_mapper.core.device_matching import resolve_device_aliases, score_device_match
from controller_mapper.core.state import DeviceInfo


def _dev(device_id: str, name: str) -> DeviceInfo:
    return DeviceInfo(
        device_id=device_id,
        name=name,
        num_axes=4,
        num_buttons=12,
        num_hats=1,
        backend_name="pygame",
    )


def test_role_prefers_stick_over_throttle_when_both_match_name() -> None:
    profile = ProfileConfig()
    profile.devices = {
        "x56_stick": DeviceConfig(
            match=DeviceMatchConfig(name_contains="X56", role="stick")
        ),
        "x56_throttle": DeviceConfig(
            match=DeviceMatchConfig(name_contains="X56", role="throttle")
        ),
    }
    devices = [
        _dev("pygame_0", "Saitek Pro Flight X56 Rhino Throttle"),
        _dev("pygame_1", "Saitek Pro Flight X56 Rhino Stick"),
    ]

    aliases = resolve_device_aliases(profile, devices)

    assert aliases == {
        "x56_stick": "pygame_1",
        "x56_throttle": "pygame_0",
    }


def test_blank_name_contains_uses_role_when_available() -> None:
    profile = ProfileConfig()
    profile.devices = {
        "joystick": DeviceConfig(
            match=DeviceMatchConfig(name_contains="", role="stick")
        )
    }
    devices = [
        _dev("pygame_0", "Generic Throttle"),
        _dev("pygame_1", "Generic Joystick"),
    ]

    aliases = resolve_device_aliases(profile, devices)

    assert aliases == {"joystick": "pygame_1"}


def test_name_mismatch_is_not_candidate() -> None:
    config = DeviceConfig(match=DeviceMatchConfig(name_contains="X56", role="stick"))

    assert score_device_match(config, _dev("pygame_0", "T.16000M Joystick")) is None

def test_name_matching_ignores_punctuation() -> None:
    config = DeviceConfig(match=DeviceMatchConfig(name_contains="X56", role="stick"))

    assert score_device_match(config, _dev("pygame_0", "Saitek Pro Flight X-56 Rhino Stick")) is not None