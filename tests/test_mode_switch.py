"""モード切替のテスト.

設計書 §6, §14 テスト方針 に対応.
"""
import pytest
from controller_mapper.transforms.mode_switch import ModeManager


class TestModeManager:
    """ModeManager の単体テスト."""

    def test_initial_mode(self) -> None:
        """指定したデフォルトモードで初期化されること."""
        m = ModeManager(definitions=["nav", "aa", "ag"], default="nav")
        assert m.current == "nav"

    def test_initial_mode_fallback(self) -> None:
        """存在しないデフォルトを指定した場合は最初のモードになること."""
        m = ModeManager(definitions=["nav", "aa", "ag"], default="unknown")
        assert m.current == "nav"

    def test_cycle_forward(self) -> None:
        """cycle() でモードが順に切り替わること."""
        m = ModeManager(definitions=["nav", "aa", "ag"], default="nav")
        assert m.cycle() == "aa"
        assert m.cycle() == "ag"
        assert m.cycle() == "nav"  # 循環

    def test_cycle_wraps_around(self) -> None:
        """最後のモードから cycle() すると最初に戻ること."""
        m = ModeManager(definitions=["a", "b"], default="b")
        assert m.cycle() == "a"

    def test_set_mode_valid(self) -> None:
        """有効なモード名を指定すると切り替わること."""
        m = ModeManager(definitions=["nav", "aa", "ag"], default="nav")
        m.set_mode("ag")
        assert m.current == "ag"

    def test_set_mode_invalid_ignored(self) -> None:
        """無効なモード名を指定しても変化しないこと."""
        m = ModeManager(definitions=["nav", "aa", "ag"], default="nav")
        m.set_mode("invalid")
        assert m.current == "nav"

    def test_matches_wildcard(self) -> None:
        """ルールの mode が \"*\" のとき常にマッチすること."""
        m = ModeManager(definitions=["nav", "aa"], default="nav")
        assert m.matches("*") is True

    def test_matches_current_mode(self) -> None:
        """現在のモードと同じ名前でマッチすること."""
        m = ModeManager(definitions=["nav", "aa"], default="nav")
        assert m.matches("nav") is True
        assert m.matches("aa") is False

    def test_matches_after_cycle(self) -> None:
        """cycle() 後に新しいモードでマッチすること."""
        m = ModeManager(definitions=["nav", "aa"], default="nav")
        m.cycle()
        assert m.matches("nav") is False
        assert m.matches("aa") is True

    def test_empty_definitions_fallback(self) -> None:
        """空のdefinitionsを渡すとdefaultリストになること."""
        m = ModeManager(definitions=[], default="default")
        assert m.current == "default"
        # cycle しても1個しかないので同じ
        assert m.cycle() == "default"

    def test_single_mode(self) -> None:
        """モードが1つだけの場合、cycle は同じモードを返すこと."""
        m = ModeManager(definitions=["only"], default="only")
        assert m.cycle() == "only"
