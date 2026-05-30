"""axis→button 変換のテスト.

設計書 §14.1 ヒステリシステスト に対応.
"""
import pytest
from controller_mapper.transforms.axis_to_button import AxisToButtonTransform, AxisToDualButtonTransform


class TestAxisToButtonTransform:
    """AxisToButtonTransform の単体テスト."""

    def test_hysteresis_basic(self) -> None:
        """設計書 §14.1 のヒステリシステスト例.

        on_threshold = 0.65
        off_threshold = 0.50

        入力: 0.60 → 0.66 → 0.62 → 0.51 → 0.49
        期待: OFF → ON  → ON  → ON  → OFF
        """
        f = AxisToButtonTransform(on_threshold=0.65, off_threshold=0.50)

        assert f.process(0.60) is False   # OFF: 0.65未満なのでONにならない
        assert f.process(0.66) is True    # ON: 閾値を超えた
        assert f.process(0.62) is True    # ON: 0.50を下回っていないのでON維持
        assert f.process(0.51) is True    # ON: 0.50を下回っていない (0.51 > 0.50)
        assert f.process(0.49) is False   # OFF: 0.50以下でOFF

    def test_no_oscillation_at_threshold(self) -> None:
        """閾値付近で振動してもON/OFFが連打されないこと (ヒステリシスの効果)."""
        f = AxisToButtonTransform(on_threshold=0.65, off_threshold=0.50)
        # ONにする
        f.process(0.70)
        # 0.55〜0.60 で振動
        for _ in range(10):
            assert f.process(0.55) is True   # OFF閾値0.50を超えているのでON維持
            assert f.process(0.60) is True

    def test_not_on_before_threshold(self) -> None:
        """閾値に届かない場合はOFFのまま."""
        f = AxisToButtonTransform(on_threshold=0.65, off_threshold=0.50)
        for v in [0.0, 0.30, 0.50, 0.64]:
            assert f.process(v) is False


class TestAxisToDualButtonTransform:
    """AxisToDualButtonTransform の単体テスト."""

    def test_positive_direction(self) -> None:
        """正方向に軸が動いたとき positive_button が ON になること."""
        f = AxisToDualButtonTransform(
            neg_on=-0.60, neg_off=-0.45,
            pos_on=0.60, pos_off=0.45,
        )
        neg, pos = f.process(0.70)
        assert pos is True
        assert neg is False

    def test_negative_direction(self) -> None:
        """負方向に軸が動いたとき negative_button が ON になること."""
        f = AxisToDualButtonTransform(
            neg_on=-0.60, neg_off=-0.45,
            pos_on=0.60, pos_off=0.45,
        )
        neg, pos = f.process(-0.70)
        assert neg is True
        assert pos is False

    def test_center_both_off(self) -> None:
        """中央では両方OFFになること."""
        f = AxisToDualButtonTransform(
            neg_on=-0.60, neg_off=-0.45,
            pos_on=0.60, pos_off=0.45,
        )
        neg, pos = f.process(0.0)
        assert neg is False
        assert pos is False
