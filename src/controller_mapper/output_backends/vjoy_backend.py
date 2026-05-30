"""出力バックエンド: vJoy.

設計書 §10 に対応.
Windows専用. pyvjoyが未インストールの場合はNullBackendにフォールバックする.

注意: vJoyはWindows 11環境での動作確認が必要.
     Windows 11向けフォーク版の使用を推奨.
"""
from __future__ import annotations

import logging

from controller_mapper.core.errors import OutputBackendError
from controller_mapper.core.state import OutputState
from controller_mapper.output_backends.base import OutputBackend

logger = logging.getLogger(__name__)

# vJoy軸名 → pyvjoy定数マッピング
AXIS_NAME_MAP = {
    "x":       0x30,  # HID_USAGE_X
    "y":       0x31,  # HID_USAGE_Y
    "z":       0x32,  # HID_USAGE_Z
    "rx":      0x33,  # HID_USAGE_RX
    "ry":      0x34,  # HID_USAGE_RY
    "rz":      0x35,  # HID_USAGE_RZ
    "slider1": 0x36,  # HID_USAGE_SL0
    "slider2": 0x37,  # HID_USAGE_SL1
}

# vJoyの軸値域は 0x0001 〜 0x7FFF (16383)
VJOY_AXIS_MAX = 0x7FFF
VJOY_AXIS_MIN = 0x0001
VJOY_AXIS_CENTER = (VJOY_AXIS_MAX + VJOY_AXIS_MIN) // 2


def _float_to_vjoy(value: float) -> int:
    """-1.0〜1.0 の float を vJoy整数値に変換する."""
    clamped = max(-1.0, min(1.0, float(value)))
    return int((clamped + 1.0) / 2.0 * (VJOY_AXIS_MAX - VJOY_AXIS_MIN) + VJOY_AXIS_MIN)


class VJoyBackend(OutputBackend):
    """vJoy仮想ジョイスティック出力バックエンド.

    Args:
        device_id: vJoyデバイスID (1オリジン)
    """

    def __init__(self, device_id: int = 1) -> None:
        self.device_id = device_id
        self._vjoy = None
        self._device = None
        self._connected = False

    @property
    def backend_name(self) -> str:
        return "vjoy"

    @property
    def is_connected(self) -> bool:
        return self._connected

    def initialize(self) -> None:
        try:
            import pyvjoy
            self._vjoy = pyvjoy
            self._device = pyvjoy.VJoyDevice(self.device_id)
            self._device.reset()
            self._connected = True
            logger.info("vJoy デバイス %d に接続しました", self.device_id)
        except ImportError:
            raise OutputBackendError(
                "pyvjoyが見つかりません。pip install pyvjoy を実行してください (Windows専用)"
            )
        except Exception as e:
            raise OutputBackendError(f"vJoy初期化失敗 (デバイスID={self.device_id}): {e}") from e

    def shutdown(self) -> None:
        if self._device is not None:
            try:
                self._device.reset()
            except Exception:
                pass
        self._connected = False
        logger.info("vJoy バックエンド終了")

    def write(self, state: OutputState) -> None:
        if not self._connected or self._device is None:
            return
        try:
            # 軸の書き込み
            for axis_name, value in state.axes.items():
                usage = AXIS_NAME_MAP.get(axis_name.lower())
                if usage is not None:
                    self._device.set_axis(usage, _float_to_vjoy(value))

            # ボタンの書き込み (1オリジン)
            for btn_idx, pressed in state.buttons.items():
                self._device.set_button(btn_idx + 1, int(pressed))

        except Exception as e:
            logger.error("vJoy書き込みエラー: %s", e)
