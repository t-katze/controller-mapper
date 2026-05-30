"""デバウンスフィルタのテスト.

設計書 §14 テスト方針 に対応.
"""
import pytest
from controller_mapper.filters.debounce import DebounceFilter


class TestDebounceFilter:
    """DebounceFilter の単体テスト."""

    def test_short_noise_is_ignored(self) -> None:
        """5ms のノイズ (短いONパルス) はOFFのままになること.

        設計書 §14.1 ボタンノイズテスト:
          入力: OFF, OFF, ON(5ms), OFF, OFF
          期待: ずっとOFF
        """
        f = DebounceFilter(debounce_ms=30.0, minimum_on_ms=20.0, minimum_off_ms=20.0)

        t = 0.0
        # OFF状態が安定している
        assert f.process(False, now=t) is False

        # 突然5ms だけ ON
        t += 0.001
        assert f.process(True, now=t) is False  # デバウンス期間中

        t += 0.005  # 5ms 後
        assert f.process(False, now=t) is False  # まだデバウンス未達

        # OFF に戻ってデバウンス安定
        t += 0.050
        assert f.process(False, now=t) is False

    def test_stable_on_is_confirmed(self) -> None:
        """十分な時間ONが続いた場合はONになること."""
        f = DebounceFilter(debounce_ms=30.0, minimum_on_ms=20.0, minimum_off_ms=20.0)
        t = 0.0
        f.process(False, now=t)

        # ONに切り替え
        t += 0.001
        f.process(True, now=t)

        # デバウンス + 最小ON時間 を超える
        t += 0.060  # 60ms 後
        result = f.process(True, now=t)
        assert result is True

    def test_toggle_mode(self) -> None:
        """トグルモード: 押すたびにON/OFF反転すること."""
        f = DebounceFilter(debounce_ms=0.0, minimum_on_ms=0.0, minimum_off_ms=0.0, toggle=True)
        t = 0.0

        # 最初は OFF
        assert f.process(False, now=t) is False

        # 1回目の押下 (OFF→ON で立ち上がり) → toggle=True
        t += 0.1
        f.process(True, now=t)
        t += 0.1
        result = f.process(False, now=t)
        # トグルがONになっているはず
        assert result is True

        # 2回目の押下 → toggle=False
        t += 0.1
        f.process(True, now=t)
        t += 0.1
        result = f.process(False, now=t)
        assert result is False

    def test_minimum_off_ignored(self) -> None:
        """最小OFF時間より短いOFF抜けは無視されること."""
        f = DebounceFilter(debounce_ms=0.0, minimum_on_ms=0.0, minimum_off_ms=50.0)
        t = 0.0

        # ON を確定させる
        f.process(True, now=t)
        t += 0.001
        result_on = f.process(True, now=t)
        assert result_on is True

        # 10ms だけ OFF に切り替わる
        t += 0.010
        result = f.process(False, now=t)
        # まだ minimum_off_ms 未達なのでONのまま
        assert result is True

        # 60ms 後 → OFFが確定
        t += 0.060
        result = f.process(False, now=t)
        assert result is False
