"""フィルタ: ヒステリシス.

設計書 §4.4, §5.3 に対応.
ON/OFF に異なる閾値を設けて振動を防ぐ.
"""
from __future__ import annotations


class HysteresisFilter:
    """ヒステリシスフィルタ (軸→論理状態変換).

    on_threshold > off_threshold の関係にしてください.

    Args:
        on_threshold:  ONに切り替わる閾値
        off_threshold: OFFに切り替わる閾値
        initial_state: 初期状態
    """

    def __init__(
        self,
        on_threshold: float = 0.65,
        off_threshold: float = 0.50,
        initial_state: bool = False,
    ) -> None:
        self.on_threshold = on_threshold
        self.off_threshold = off_threshold
        self._state = initial_state

    def process(self, value: float) -> bool:
        """軸値を受け取りヒステリシスを適用した論理値を返す."""
        if not self._state and value >= self.on_threshold:
            self._state = True
        elif self._state and value <= self.off_threshold:
            self._state = False
        return self._state

    def reset(self) -> None:
        self._state = False
