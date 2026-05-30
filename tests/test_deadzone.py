"""デッドゾーンフィルタのテスト.

設計書 §14 テスト方針 に対応.
"""
import pytest
from controller_mapper.filters.deadzone import DeadzoneFilter


class TestDeadzoneFilter:
    """DeadzoneFilter の単体テスト."""

    def test_center_deadzone_returns_zero(self) -> None:
        """デッドゾーン内の値は 0 を返すこと."""
        f = DeadzoneFilter(deadzone=0.10)
        assert f.process(0.05) == pytest.approx(0.0)
        assert f.process(-0.09) == pytest.approx(0.0)
        assert f.process(0.0) == pytest.approx(0.0)

    def test_outside_deadzone_remapped(self) -> None:
        """デッドゾーン外の値は 0〜1 に線形マッピングされること."""
        f = DeadzoneFilter(deadzone=0.10)
        # 0.10 ちょうど → 0.0 (境界)
        result = f.process(0.10)
        assert result == pytest.approx(0.0, abs=1e-6)
        # 1.0 → 1.0
        result = f.process(1.0)
        assert result == pytest.approx(1.0)

    def test_end_deadzone_clamps_to_max(self) -> None:
        """エンドデッドゾーン内の値は ±1.0 に張り付くこと."""
        f = DeadzoneFilter(end_deadzone=0.05)
        assert f.process(0.96) == pytest.approx(1.0)
        assert f.process(-0.97) == pytest.approx(-1.0)

    def test_invert(self) -> None:
        """invert=True のとき符号が反転すること."""
        f = DeadzoneFilter(deadzone=0.05, invert=True)
        result = f.process(0.5)
        assert result < 0

    def test_value_clamped(self) -> None:
        """出力は -1.0〜1.0 にクランプされること."""
        f = DeadzoneFilter()
        assert f.process(2.0) == pytest.approx(1.0)
        assert f.process(-2.0) == pytest.approx(-1.0)

    def test_both_deadzones(self) -> None:
        """センター・エンドデッドゾーンを両方設定した場合のテスト."""
        f = DeadzoneFilter(deadzone=0.10, end_deadzone=0.10)
        # 範囲: 0.10〜0.90 → 0.0〜1.0
        assert f.process(0.10) == pytest.approx(0.0, abs=1e-6)
        assert f.process(0.90) == pytest.approx(1.0)
        assert f.process(0.50) == pytest.approx(0.5, abs=0.01)
