"""入力バックエンド: pygame.joystick.

設計書 §10 に対応.
"""
from __future__ import annotations

import logging

from controller_mapper.core.errors import InputBackendError
from controller_mapper.core.state import DeviceInfo, DeviceState
from controller_mapper.input_backends.base import InputBackend

logger = logging.getLogger(__name__)


class PygameBackend(InputBackend):
    """pygame.joystick を使った入力バックエンド."""

    def __init__(self) -> None:
        self._joysticks: dict[int, object] = {}
        self._ignored_count = 0
        self._initialized = False

    @property
    def backend_name(self) -> str:
        return "pygame"

    def initialize(self) -> None:
        try:
            import pygame

            pygame.init()
            pygame.joystick.init()
            self._pygame = pygame
            self._initialized = True
            count = pygame.joystick.get_count()
            logger.info("pygame バックエンド初期化完了: %d デバイス検出", count)
            self._scan_joysticks()
        except ImportError as e:
            raise InputBackendError("pygameが見つかりません: pip install pygame") from e
        except Exception as e:
            raise InputBackendError(f"pygame初期化失敗: {e}") from e

    def _scan_joysticks(self) -> None:
        self._joysticks.clear()
        self._ignored_count = 0
        count = self._pygame.joystick.get_count()
        for i in range(count):
            joy = self._pygame.joystick.Joystick(i)
            joy.init()
            name = joy.get_name()
            if self._is_ignored_input_device(name):
                self._ignored_count += 1
                try:
                    joy.quit()
                except Exception:
                    pass
                logger.info("  [%d] %s (入力から除外)", i, name)
                continue
            self._joysticks[i] = joy
            logger.info("  [%d] %s", i, name)
        logger.info(
            "入力対象デバイス: %d 台 (除外: %d 台)",
            len(self._joysticks),
            self._ignored_count,
        )

    def shutdown(self) -> None:
        if self._initialized:
            self._pygame.joystick.quit()
            self._pygame.quit()
            self._initialized = False
            logger.info("pygame バックエンド終了")

    def get_devices(self) -> list[DeviceInfo]:
        if not self._initialized:
            return []
        devices = []
        for idx, joy in self._joysticks.items():
            guid = ""
            try:
                guid = joy.get_guid()
            except Exception:
                pass
            devices.append(DeviceInfo(
                device_id=self._device_id(idx),
                name=joy.get_name(),
                num_axes=joy.get_numaxes(),
                num_buttons=joy.get_numbuttons(),
                num_hats=joy.get_numhats(),
                backend_name=self.backend_name,
                guid=guid,
            ))
        return devices

    def rescan(self) -> None:
        """デバイスを再スキャンする (「再スキャン」ボタン用)."""
        if self._initialized:
            self._pygame.joystick.quit()
            self._pygame.joystick.init()
            self._scan_joysticks()
            logger.info("再スキャン完了: %d デバイス", len(self._joysticks))

    def poll(self) -> dict[str, DeviceState]:
        if not self._initialized:
            return {}
        # イベントキューを処理してjoystickの値を更新
        self._pygame.event.pump()

        result: dict[str, DeviceState] = {}
        for idx, joy in self._joysticks.items():
            dev_id = self._device_id(idx)
            state = DeviceState()
            for a in range(joy.get_numaxes()):
                state.axes[a] = float(joy.get_axis(a))
            for b in range(joy.get_numbuttons()):
                state.buttons[b] = bool(joy.get_button(b))
            for h in range(joy.get_numhats()):
                state.hats[h] = tuple(joy.get_hat(h))  # type: ignore[assignment]
            result[dev_id] = state
        return result

    @staticmethod
    def _is_ignored_input_device(name: str) -> bool:
        return "vjoy" in name.lower()

    @staticmethod
    def _device_id(index: int) -> str:
        return f"pygame_{index}"
