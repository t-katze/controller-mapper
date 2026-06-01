"""カーブフィルタのテスト.

設計書 §14 テスト方針 に対応.
"""
import pytest
from controller_mapper.filters.curve import CurveFilter


class TestCurveFilter:
    """CurveFilter の単体テスト."""

    def test_linear_passthrough(self) -> None:
        """exponent=1.0 のとき入力値がそのまま返ること."""
        f = CurveFilter(exponent=1.0)
        assert f.process(0.5) == pytest.approx(0.5)
        assert f.process(-0.5) == pytest.approx(-0.5)
        assert f.process(0.0) == pytest.approx(0.0)
        assert f.process(1.0) == pytest.approx(1.0)

    def test_exponent_greater_than_one_reduces_sensitivity(self) -> None:
        """exponent>1 のとき中央付近の感度が低下すること (精密操作向け)."""
        f = CurveFilter(exponent=2.0)
        # |0.5|^2 = 0.25
        assert f.process(0.5) == pytest.approx(0.25)
        assert f.process(-0.5) == pytest.approx(-0.25)

    def test_exponent_less_than_one_increases_sensitivity(self) -> None:
        """exponent<1 のとき中央付近の感度が上がること."""
        f = CurveFilter(exponent=0.5)
        # |0.25|^0.5 = 0.5
        assert f.process(0.25) == pytest.approx(0.5)

    def test_extremes_unchanged(self) -> None:
        """0.0 と ±1.0 はカーブに関わらず変わらないこと."""
        for exp in [0.5, 1.0, 2.0, 3.0]:
            f = CurveFilter(exponent=exp)
            assert f.process(0.0) == pytest.approx(0.0)
            assert f.process(1.0) == pytest.approx(1.0)
            assert f.process(-1.0) == pytest.approx(-1.0)

    def test_sign_preserved(self) -> None:
        """正の入力は正、負の入力は負を返すこと."""
        f = CurveFilter(exponent=1.5)
        assert f.process(0.7) > 0
        assert f.process(-0.7) < 0

    def test_clamped_input(self) -> None:
        """入力が ±1.0 を超えている場合はクランプされること."""
        f = CurveFilter(exponent=2.0)
        assert f.process(1.5) == pytest.approx(1.0)
        assert f.process(-1.5) == pytest.approx(-1.0)

    def test_minimum_exponent(self) -> None:
        """exponent に 0 以下を指定しても 0.01 にクランプされること."""
        f = CurveFilter(exponent=0.0)
        assert f.exponent == pytest.approx(0.01)
        f2 = CurveFilter(exponent=-1.0)
        assert f2.exponent == pytest.approx(0.01)
