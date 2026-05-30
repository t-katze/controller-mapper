"""変換: button → axis.

設計書 §5.4 に対応.
"""
from __future__ import annotations

import time


class ButtonToAxisTransform:
    """ボタンON/OFFを軸値に変換する.

    Args:
        released_value: ボタンOFF時の軸値
        pressed_value:  ボタンON時の軸値
    """

    def __init__(self, released_value: float = 0.0, pressed_value: float = 1.0) -> None:
        self.released_value = released_value
        self.pressed_value = pressed_value

    def process(self, pressed: bool) -> float:
        return self.pressed_value if pressed else self.released_value


class ButtonPairToAxisTransform:
    """2つのボタンで1軸を操作する.

    mode='direct': ボタンに対応する固定値を返す
    mode='ramp':   ボタンを押している間、速度 speed_per_sec で値が増減する

    Args:
        mode:            'direct' | 'ramp'
        speed_per_sec:   rampモードの変化速度 (1.0 = 1秒で0→1)
        return_to_center: ボタンを離したとき中央(0.0)に戻す
    """

    def __init__(
        self,
        mode: str = "ramp",
        speed_per_sec: float = 0.8,
        return_to_center: bool = False,
    ) -> None:
        self.mode = mode
        self.speed_per_sec = speed_per_sec
        self.return_to_center = return_to_center
        self._value: float = 0.0
        self._last_t: float | None = None

    def process(
        self,
        neg_pressed: bool,
        pos_pressed: bool,
        now: float | None = None,
    ) -> float:
        """(負方向ボタン, 正方向ボタン) を受け取り軸値を返す."""
        t = now if now is not None else time.monotonic()

        if self.mode == "direct":
            if neg_pressed and not pos_pressed:
                self._value = -1.0
            elif pos_pressed and not neg_pressed:
                self._value = 1.0
            elif not neg_pressed and not pos_pressed:
                if self.return_to_center:
                    self._value = 0.0
        else:  # ramp
            if self._last_t is not None:
                dt = t - self._last_t
                direction = 0.0
                if neg_pressed and not pos_pressed:
                    direction = -1.0
                elif pos_pressed and not neg_pressed:
                    direction = 1.0
                elif not neg_pressed and not pos_pressed and self.return_to_center:
                    # 中央に向かってランプ
                    direction = -1.0 if self._value > 0 else 1.0 if self._value < 0 else 0.0

                self._value += direction * self.speed_per_sec * dt
                self._value = max(-1.0, min(1.0, self._value))

        self._last_t = t
        return self._value

    def reset(self) -> None:
        self._value = 0.0
        self._last_t = None
