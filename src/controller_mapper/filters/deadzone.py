"""フィルタ: デッドゾーン.

設計書 §4.4 に対応.
"""
from __future__ import annotations


class DeadzoneFilter:
    """軸デッドゾーンフィルタ.

    センターデッドゾーン: |x| < deadzone なら 0 を返す.
    エンドデッドゾーン:  |x| > (1 - end_deadzone) なら ±1 に張り付ける.
    両方を適用した場合は残余範囲を 0〜1 に線形マッピングする.

    Args:
        deadzone:     センターデッドゾーン幅 (0.0〜1.0)
        end_deadzone: エンドデッドゾーン幅 (0.0〜1.0)
        invert:       True のとき出力を反転する
    """

    def __init__(
        self,
        deadzone: float = 0.0,
        end_deadzone: float = 0.0,
        invert: bool = False,
    ) -> None:
        self.deadzone = max(0.0, min(1.0, deadzone))
        self.end_deadzone = max(0.0, min(1.0, end_deadzone))
        self.invert = invert

    def process(self, value: float) -> float:
        """軸値を受け取りデッドゾーン処理後の値を返す.

        Args:
            value: 生軸値 (-1.0 〜 1.0)

        Returns:
            処理後の軸値 (-1.0 〜 1.0)
        """
        v = float(value)
        sign = 1.0 if v >= 0 else -1.0
        abs_v = abs(v)

        # センターデッドゾーン
        if abs_v <= self.deadzone:
            result = 0.0
        else:
            # エンドデッドゾーン
            high = 1.0 - self.end_deadzone
            if abs_v >= high:
                result = sign * 1.0
            else:
                # 残余範囲を 0〜1 にリマップ
                span = high - self.deadzone
                if span <= 0.0:
                    result = sign * 1.0
                else:
                    result = sign * (abs_v - self.deadzone) / span

        if self.invert:
            result = -result

        return max(-1.0, min(1.0, result))
