"""フィルタ: 感度カーブ.

設計書 §4.4 に対応.
"""
from __future__ import annotations

import math


class CurveFilter:
    """指数カーブフィルタ.

    f(x) = sign(x) * |x|^exponent

    exponent > 1: 中央付近が鈍感（精密操作向け）
    exponent < 1: 中央付近が敏感
    exponent = 1: リニア（変化なし）

    Args:
        exponent: カーブ指数 (正の実数)
    """

    def __init__(self, exponent: float = 1.0) -> None:
        self.exponent = max(0.01, float(exponent))

    def process(self, value: float) -> float:
        """軸値にカーブを適用して返す.

        Args:
            value: 入力軸値 (-1.0 〜 1.0)

        Returns:
            カーブ適用後の軸値 (-1.0 〜 1.0)
        """
        v = max(-1.0, min(1.0, float(value)))
        if v == 0.0:
            return 0.0
        sign = 1.0 if v > 0 else -1.0
        return sign * (abs(v) ** self.exponent)
