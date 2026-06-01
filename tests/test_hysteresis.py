"""ヒステリシスフィルタの単体テスト.

設計書 §14.1 ヒステリシステスト に対応.
"""
import pytest
from controller_mapper.filters.hysteresis import HysteresisFilter


class TestHysteresisFilter:
    """HysteresisFilter の単体テスト."""

    def test_design_doc_example(self) -> None:
        """設計書 §14.1 のヒステリシステスト例.

        on_threshold = 0.65
        off_threshold = 0.50

        入力: 0.60 → 0.66 → 0.62 → 0.51 → 0.49
        期待: OFF → ON  → ON  → ON  → OFF
        """
        f = HysteresisFilter(on_threshold=0.65, off_threshold=0.50)
        assert f.process(0.60) is False
        assert f.process(0.66) is True
        assert f.process(0.62) is True
        assert f.process(0.51) is True
        assert f.process(0.49) is False

    def test_initially_off(self) -> None:
        """初期状態は OFF であること."""
        f = HysteresisFilter(on_threshold=0.65, off_threshold=0.50)
        assert f.process(0.0) is False

    def test_initially_on(self) -> None:
        """initial_state=True のとき最初から ON であること."""
        f = HysteresisFilter(on_threshold=0.65, off_threshold=0.50, initial_state=True)
        assert f.process(0.55) is True  # OFF閾値を超えているのでON維持

    def test_no_oscillation_near_threshold(self) -> None:
        """閾値付近で振動してもON/OFFが連打されないこと."""
        f = HysteresisFilter(on_threshold=0.65, off_threshold=0.50)
        # 最初にONにする
        f.process(0.70)
        # 0.55〜0.60 で振動
        for _ in range(20):
            assert f.process(0.55) is True
            assert f.process(0.60) is True

    def test_off_exactly_at_threshold(self) -> None:
        """off_threshold ちょうどでOFFになること."""
        f = HysteresisFilter(on_threshold=0.65, off_threshold=0.50)
        f.process(0.70)  # ON
        assert f.process(0.50) is False  # ちょうど0.50でOFF

    def test_on_exactly_at_threshold(self) -> None:
        """on_threshold ちょうどでONになること."""
        f = HysteresisFilter(on_threshold=0.65, off_threshold=0.50)
        assert f.process(0.65) is True

    def test_reset(self) -> None:
        """reset() 後は OFF に戻ること."""
        f = HysteresisFilter(on_threshold=0.65, off_threshold=0.50)
        f.process(0.70)  # ON
        f.reset()
        assert f.process(0.55) is False  # ON閾値未達なのでOFF

    def test_negative_values(self) -> None:
        """負の閾値でも正しく動作すること."""
        f = HysteresisFilter(on_threshold=-0.30, off_threshold=-0.50)
        assert f.process(-0.20) is True   # -0.20 >= -0.30 → ON
        assert f.process(-0.40) is True   # -0.40 > -0.50 → ON維持
        assert f.process(-0.50) is False  # -0.50 <= -0.50 → OFF
