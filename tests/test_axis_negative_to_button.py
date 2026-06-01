"""軸の-方向→ボタン変換のテスト.

設計書 §5.3 拡張: 軸の負方向だけをボタンに変換する.
"""
import pytest
from controller_mapper.transforms.axis_to_button import AxisToButtonTransform


class TestAxisNegativeToButton:
    """AxisToButtonTransform (negative=True) の単体テスト."""

    def test_negative_direction_trigger(self) -> None:
        """軸が-方向に十分動いたらONになること.

        例: 左ブレーキ軸 (値が-0.7 のとき ON)
        """
        f = AxisToButtonTransform(on_threshold=0.65, off_threshold=0.50, negative=True)
        # 軸が -0.7 → 反転して 0.7 → on_threshold(0.65) を超える → ON
        assert f.process(-0.7) is True
        # 軸が -0.3 → 反転して 0.3 → off_threshold(0.50) 以下 → OFF
        assert f.process(-0.3) is False

    def test_negative_direction_hysteresis(self) -> None:
        """ヒステリシスが-方向でも正しく動作すること."""
        f = AxisToButtonTransform(on_threshold=0.65, off_threshold=0.50, negative=True)
        assert f.process(-0.60) is False   # 0.60 < 0.65 → OFF
        assert f.process(-0.66) is True    # 0.66 > 0.65 → ON
        assert f.process(-0.55) is True    # 0.55 > 0.50 → ON維持 (ヒステリシス)
        assert f.process(-0.49) is False   # 0.49 < 0.50 → OFF

    def test_negative_thresholds_are_accepted(self) -> None:
        """負方向指定では負の閾値も正の閾値と同じ意味で扱うこと."""
        f = AxisToButtonTransform(on_threshold=-0.65, off_threshold=-0.50, negative=True)
        assert f.process(-0.7) is True
        assert f.process(-0.3) is False

    def test_negative_direction_ignores_positive(self) -> None:
        """positive=True でも negative=True のとき正方向の入力はOFFのままであること."""
        f = AxisToButtonTransform(on_threshold=0.65, off_threshold=0.50, negative=True)
        # 正方向 → 反転して負 → 閾値に届かない → OFF
        assert f.process(0.9) is False
        assert f.process(1.0) is False

    def test_positive_direction_unchanged(self) -> None:
        """negative=False (デフォルト) のとき従来どおり正方向で判定すること."""
        f = AxisToButtonTransform(on_threshold=0.65, off_threshold=0.50, negative=False)
        assert f.process(0.7) is True
        assert f.process(-0.7) is False  # 負方向はOFFのまま

    def test_negative_no_oscillation(self) -> None:
        """ヒステリシスにより閾値付近での振動が防止されること."""
        f = AxisToButtonTransform(on_threshold=0.65, off_threshold=0.50, negative=True)
        f.process(-0.70)  # ON
        for _ in range(20):
            assert f.process(-0.55) is True   # OFF閾値(0.50)を超えているのでON維持
            assert f.process(-0.60) is True

    def test_center_is_off(self) -> None:
        """中央 (0.0) は常にOFFであること."""
        f = AxisToButtonTransform(on_threshold=0.65, off_threshold=0.50, negative=True)
        assert f.process(0.0) is False
