"""フィルタ: 移動平均スムージング.

設計書 §4.4 に対応.
注意: 主操縦軸には強いスムージングをかけすぎないこと.
     ダイヤル・スライダー類に適している.
"""
from __future__ import annotations

from collections import deque


class SmoothingFilter:
    """移動平均スムージングフィルタ.

    Args:
        window: 平均を取るサンプル数 (1 = 無効)
    """

    def __init__(self, window: int = 1) -> None:
        self.window = max(1, int(window))
        self._buf: deque[float] = deque(maxlen=self.window)

    def process(self, value: float) -> float:
        """軸値を受け取りスムージング後の値を返す."""
        self._buf.append(float(value))
        return sum(self._buf) / len(self._buf)

    def reset(self) -> None:
        self._buf.clear()


class EwmaFilter:
    """指数移動平均 (EWMA) フィルタ.

    alpha が小さいほど平滑化が強い (遅延増大).
    alpha = 1.0 で無効 (生値をそのまま返す).

    Args:
        alpha: 平滑化係数 (0.0〜1.0)
    """

    def __init__(self, alpha: float = 1.0) -> None:
        self.alpha = max(0.0, min(1.0, float(alpha)))
        self._last: float | None = None

    def process(self, value: float) -> float:
        v = float(value)
        if self._last is None:
            self._last = v
        else:
            self._last = self.alpha * v + (1.0 - self.alpha) * self._last
        return self._last

    def reset(self) -> None:
        self._last = None
