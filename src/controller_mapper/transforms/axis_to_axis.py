"""変換: axis → axis.

設計書 §5.2 に対応.
"""
from __future__ import annotations

from controller_mapper.filters.curve import CurveFilter
from controller_mapper.filters.deadzone import DeadzoneFilter
from controller_mapper.filters.smoothing import EwmaFilter


class AxisToAxisTransform:
    """物理軸を仮想軸へマッピングする.

    フィルタを順に適用: deadzone → curve → smoothing
    """

    def __init__(
        self,
        deadzone: float = 0.0,
        end_deadzone: float = 0.0,
        curve: float = 1.0,
        invert: bool = False,
        smoothing_alpha: float = 1.0,
    ) -> None:
        self._dz = DeadzoneFilter(deadzone, end_deadzone, invert)
        self._curve = CurveFilter(curve)
        self._smooth = EwmaFilter(smoothing_alpha)

    def process(self, value: float) -> float:
        """軸値を変換して返す."""
        v = self._dz.process(value)
        v = self._curve.process(v)
        v = self._smooth.process(v)
        return v
