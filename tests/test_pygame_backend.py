"""pygame入力バックエンドのデバイス除外テスト."""

from controller_mapper.input_backends.pygame_backend import PygameBackend


def test_vjoy_is_ignored_as_input_device() -> None:
    assert PygameBackend._is_ignored_input_device("vJoy Device") is True
    assert PygameBackend._is_ignored_input_device("Controller (vJoy Device)") is True


def test_non_vjoy_device_is_not_ignored() -> None:
    assert PygameBackend._is_ignored_input_device("Logitech X56 H.O.T.A.S.") is False