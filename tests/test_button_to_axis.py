"""button→axis 変換のテスト.

設計書 §5.4, §14 テスト方針 に対応.
"""
import pytest
from controller_mapper.transforms.button_to_axis import ButtonToAxisTransform, ButtonPairToAxisTransform


class TestButtonToAxisTransform:
    """ButtonToAxisTransform の単体テスト."""

    def test_pressed_returns_pressed_value(self) -> None:
        f = ButtonToAxisTransform(released_value=0.0, pressed_value=1.0)
        assert f.process(True) == pytest.approx(1.0)

    def test_released_returns_released_value(self) -> None:
        f = ButtonToAxisTransform(released_value=0.0, pressed_value=1.0)
        assert f.process(False) == pytest.approx(0.0)

    def test_custom_values(self) -> None:
        f = ButtonToAxisTransform(released_value=-1.0, pressed_value=0.5)
        assert f.process(True) == pytest.approx(0.5)
        assert f.process(False) == pytest.approx(-1.0)


class TestButtonPairToAxisTransform:
    """ButtonPairToAxisTransform の単体テスト."""

    def test_direct_mode_positive(self) -> None:
        """directモード: pos押下で +1.0 になること."""
        f = ButtonPairToAxisTransform(mode="direct", return_to_center=True)
        result = f.process(neg_pressed=False, pos_pressed=True, now=0.0)
        assert result == pytest.approx(1.0)

    def test_direct_mode_negative(self) -> None:
        """directモード: neg押下で -1.0 になること."""
        f = ButtonPairToAxisTransform(mode="direct", return_to_center=True)
        result = f.process(neg_pressed=True, pos_pressed=False, now=0.0)
        assert result == pytest.approx(-1.0)

    def test_direct_mode_center(self) -> None:
        """directモード: 両ボタン離したとき return_to_center=True で 0.0 になること."""
        f = ButtonPairToAxisTransform(mode="direct", return_to_center=True)
        f.process(False, True, now=0.0)
        result = f.process(False, False, now=0.1)
        assert result == pytest.approx(0.0)

    def test_ramp_mode_increases(self) -> None:
        """rampモード: pos押下で値が増加すること."""
        f = ButtonPairToAxisTransform(mode="ramp", speed_per_sec=1.0, return_to_center=False)
        # 初回呼び出し (タイマー開始)
        f.process(False, True, now=0.0)
        # 0.5秒後: 0.5 になるはず
        result = f.process(False, True, now=0.5)
        assert result == pytest.approx(0.5, abs=0.01)

    def test_ramp_mode_clamped(self) -> None:
        """rampモード: 上限 1.0 でクランプされること."""
        f = ButtonPairToAxisTransform(mode="ramp", speed_per_sec=2.0, return_to_center=False)
        f.process(False, True, now=0.0)
        result = f.process(False, True, now=2.0)  # 4秒分だが最大1.0
        assert result == pytest.approx(1.0)
