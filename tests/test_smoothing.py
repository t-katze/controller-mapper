"""スムージングフィルタのテスト.

設計書 §14 テスト方針 に対応.
"""
import pytest
from controller_mapper.filters.smoothing import SmoothingFilter, EwmaFilter


class TestSmoothingFilter:
    """SmoothingFilter (移動平均) の単体テスト."""

    def test_window_one_passthrough(self) -> None:
        """window=1 のときは入力値がそのまま返ること."""
        f = SmoothingFilter(window=1)
        assert f.process(0.5) == pytest.approx(0.5)
        assert f.process(0.8) == pytest.approx(0.8)

    def test_average_of_window(self) -> None:
        """window=3 のとき直近3サンプルの平均になること."""
        f = SmoothingFilter(window=3)
        f.process(0.0)
        f.process(0.3)
        result = f.process(0.6)
        assert result == pytest.approx(0.3)  # (0.0 + 0.3 + 0.6) / 3

    def test_window_slides(self) -> None:
        """ウィンドウが満杯後、古い値が押し出されること."""
        f = SmoothingFilter(window=2)
        f.process(1.0)   # buf=[1.0]
        f.process(0.0)   # buf=[1.0, 0.0]  → avg=0.5
        result = f.process(0.0)  # buf=[0.0, 0.0] → avg=0.0
        assert result == pytest.approx(0.0)

    def test_reset_clears_buffer(self) -> None:
        """reset() 後はバッファが空になること."""
        f = SmoothingFilter(window=3)
        f.process(1.0)
        f.process(1.0)
        f.reset()
        result = f.process(0.0)
        assert result == pytest.approx(0.0)

    def test_minimum_window(self) -> None:
        """window=0 以下は 1 にクランプされること."""
        f = SmoothingFilter(window=0)
        assert f.window == 1


class TestEwmaFilter:
    """EwmaFilter (指数移動平均) の単体テスト."""

    def test_alpha_one_passthrough(self) -> None:
        """alpha=1.0 のとき入力値がそのまま返ること."""
        f = EwmaFilter(alpha=1.0)
        assert f.process(0.5) == pytest.approx(0.5)
        assert f.process(0.8) == pytest.approx(0.8)

    def test_alpha_zero_holds_first_value(self) -> None:
        """alpha=0.0 のとき最初の値がずっと保持されること."""
        f = EwmaFilter(alpha=0.0)
        f.process(1.0)
        assert f.process(0.0) == pytest.approx(1.0)
        assert f.process(0.0) == pytest.approx(1.0)

    def test_smoothing_effect(self) -> None:
        """0 < alpha < 1 のとき段階的に値が変化すること."""
        f = EwmaFilter(alpha=0.5)
        f.process(0.0)
        # 0.5 * 1.0 + 0.5 * 0.0 = 0.5
        result = f.process(1.0)
        assert result == pytest.approx(0.5)
        # 0.5 * 1.0 + 0.5 * 0.5 = 0.75
        result = f.process(1.0)
        assert result == pytest.approx(0.75)

    def test_reset_clears_state(self) -> None:
        """reset() 後は初回入力値が直接返ること."""
        f = EwmaFilter(alpha=0.5)
        f.process(1.0)
        f.process(1.0)
        f.reset()
        result = f.process(0.0)
        assert result == pytest.approx(0.0)

    def test_alpha_clamped(self) -> None:
        """alpha は 0.0〜1.0 にクランプされること."""
        f = EwmaFilter(alpha=2.0)
        assert f.alpha == pytest.approx(1.0)
        f2 = EwmaFilter(alpha=-1.0)
        assert f2.alpha == pytest.approx(0.0)
