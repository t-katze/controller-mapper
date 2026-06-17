"""button_split 変換のテスト.

ボタンのON/OFFを2つの仮想ボタンに分割する.
使用例: ギアスイッチ → ギアUPボタン + ギアDOWNボタン
"""
from controller_mapper.transforms.button_to_button import ButtonOffTransform, ButtonSplitTransform


class TestButtonSplitTransform:
    """ButtonSplitTransform の単体テスト."""

    def test_button_on_splits_correctly(self) -> None:
        """物理ボタンONのとき on_button=True, off_button=False になること."""
        f = ButtonSplitTransform(on_button=10, off_button=11)
        on_result, off_result = f.process(True)
        assert on_result is True
        assert off_result is False

    def test_button_off_splits_correctly(self) -> None:
        """物理ボタンOFFのとき on_button=False, off_button=True になること."""
        f = ButtonSplitTransform(on_button=10, off_button=11)
        on_result, off_result = f.process(False)
        assert on_result is False
        assert off_result is True

    def test_toggle_behavior(self) -> None:
        """ON→OFF→ON と切り替えたとき正しくスプリットされること."""
        f = ButtonSplitTransform(on_button=5, off_button=6)
        on1, off1 = f.process(True)
        assert on1 is True and off1 is False
        on2, off2 = f.process(False)
        assert on2 is False and off2 is True
        on3, off3 = f.process(True)
        assert on3 is True and off3 is False

    def test_button_indices_stored(self) -> None:
        """on_button / off_button のインデックスが保持されていること."""
        f = ButtonSplitTransform(on_button=20, off_button=21)
        assert f.on_button == 20
        assert f.off_button == 21

    def test_with_debounce(self) -> None:
        """デバウンス付きでも正しく動作すること."""
        f = ButtonSplitTransform(on_button=10, off_button=11, debounce_ms=30.0)
        t = 0.0

        # 初期状態はOFF → on=False, off=True
        on_r, off_r = f.process(False, now=t)
        assert on_r is False
        assert off_r is True

        # 5ms だけON → デバウンス未達でOFFのまま
        t += 0.005
        on_r, off_r = f.process(True, now=t)
        assert on_r is False
        assert off_r is True

        # 50ms 後もON → デバウンス確定でON
        t += 0.050
        on_r, off_r = f.process(True, now=t)
        assert on_r is True
        assert off_r is False

    def test_initial_state_off(self) -> None:
        """初期状態（何も入力していない）では off_button が True であること."""
        f = ButtonSplitTransform(on_button=0, off_button=1)
        on_r, off_r = f.process(False)
        assert on_r is False
        assert off_r is True

    def test_gap_keeps_both_outputs_off_when_switching_to_on(self) -> None:
        """OFF→ON切替時、指定時間だけ両出力ボタンがOFFになること."""
        f = ButtonSplitTransform(on_button=0, off_button=1, gap_ms=50.0)

        assert f.process(False, now=0.0) == (False, True)
        assert f.process(True, now=0.100) == (False, False)
        assert f.filtered is True
        assert f.process(True, now=0.149) == (False, False)
        assert f.process(True, now=0.151) == (True, False)

    def test_gap_keeps_both_outputs_off_when_switching_to_off(self) -> None:
        """ON→OFF切替時、指定時間だけ両出力ボタンがOFFになること."""
        f = ButtonSplitTransform(on_button=0, off_button=1, gap_ms=50.0)

        assert f.process(True, now=0.0) == (True, False)
        assert f.process(False, now=0.100) == (False, False)
        assert f.filtered is False
        assert f.process(False, now=0.149) == (False, False)
        assert f.process(False, now=0.151) == (False, True)


class TestButtonOffTransform:
    """ButtonOffTransform の単体テスト."""

    def test_button_on_releases_output(self) -> None:
        """物理ボタンONのとき出力ボタンがOFFになること."""
        f = ButtonOffTransform()
        assert f.process(True) is False

    def test_button_off_presses_output(self) -> None:
        """物理ボタンOFFのとき出力ボタンがONになること."""
        f = ButtonOffTransform()
        assert f.process(False) is True

    def test_with_debounce(self) -> None:
        """デバウンス付きでもOFF専用出力が正しく動作すること."""
        f = ButtonOffTransform(debounce_ms=30.0)
        t = 0.0

        assert f.process(False, now=t) is True

        t += 0.005
        assert f.process(True, now=t) is True

        t += 0.050
        assert f.process(True, now=t) is False
