"""変換: axis → button.

設計書 §5.3 に対応.
ヒステリシスを使って ON/OFF振動を防止する.
"""
from __future__ import annotations

from controller_mapper.filters.hysteresis import HysteresisFilter


class AxisToButtonTransform:
    """軸値が閾値を超えたらボタンONにする.

    Args:
        on_threshold:  ONになる閾値  (off_threshold より大きくすること)
        off_threshold: OFFになる閾値
        negative:      True のとき軸の負方向で判定する (値を反転してから閾値比較)
    """

    def __init__(self, on_threshold: float = 0.65, off_threshold: float = 0.50,
                 negative: bool = False) -> None:
        if negative:
            on_threshold = abs(on_threshold)
            off_threshold = abs(off_threshold)
        self._hyst = HysteresisFilter(on_threshold, off_threshold)
        self._negative = negative

    def process(self, value: float) -> bool:
        if self._negative:
            value = -value
        return self._hyst.process(value)


class AxisToDualButtonTransform:
    """軸の正負両方向をそれぞれボタンにマッピングする.

    設計書 §5.3「2方向に割り当てる場合」に対応.

    Args:
        neg_on:  負方向 ON閾値  (負の値)
        neg_off: 負方向 OFF閾値 (neg_on より大きい, 負の値)
        pos_on:  正方向 ON閾値
        pos_off: 正方向 OFF閾値 (pos_on より小さい)
    """

    def __init__(
        self,
        neg_on: float = -0.60,
        neg_off: float = -0.45,
        pos_on: float = 0.60,
        pos_off: float = 0.45,
    ) -> None:
        # 負方向は絶対値で処理するため符号を反転
        self._neg_hyst = HysteresisFilter(abs(neg_on), abs(neg_off))
        self._pos_hyst = HysteresisFilter(pos_on, pos_off)

    def process(self, value: float) -> tuple[bool, bool]:
        """(negative_button, positive_button) のタプルを返す."""
        neg = self._neg_hyst.process(-value)   # 負方向は反転して処理
        pos = self._pos_hyst.process(value)
        return neg, pos
