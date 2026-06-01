"""変換: button → button.

設計書 §5.1 に対応.
"""
from __future__ import annotations

from controller_mapper.filters.debounce import DebounceFilter


class ButtonToButtonTransform:
    """物理ボタンを仮想ボタンへマッピングする.

    デバウンスフィルタを内包する.
    """

    def __init__(self, debounce_ms: float = 0.0, minimum_on_ms: float = 0.0,
                 minimum_off_ms: float = 0.0, toggle: bool = False) -> None:
        self._debounce = DebounceFilter(
            debounce_ms=debounce_ms,
            minimum_on_ms=minimum_on_ms,
            minimum_off_ms=minimum_off_ms,
            toggle=toggle,
        )

    def process(self, raw: bool, now: float | None = None) -> bool:
        return self._debounce.process(raw, now)


class ButtonSplitTransform:
    """物理ボタンの ON/OFF を2つの仮想ボタンに分割する.

    使用例:
      - ギアスイッチ(2ポジション) → ギアUPボタン + ギアDOWNボタン
      - 安全装置スイッチ → ON時にボタンA, OFF時にボタンB

    Args:
        on_button:  物理ボタンがONのとき出力するボタンインデックス
        off_button: 物理ボタンがOFFのとき出力するボタンインデックス
        debounce_ms: デバウンス時間 (ms)
    """

    def __init__(self, on_button: int = 0, off_button: int = 1,
                 debounce_ms: float = 0.0) -> None:
        self.on_button = on_button
        self.off_button = off_button
        self._debounce = DebounceFilter(
            debounce_ms=debounce_ms,
            minimum_on_ms=0.0,
            minimum_off_ms=0.0,
        )

    def process(self, raw: bool, now: float | None = None) -> tuple[bool, bool]:
        """(on_buttonの状態, off_buttonの状態) を返す.

        物理ボタンが ON → on_button=True,  off_button=False
        物理ボタンが OFF → on_button=False, off_button=True
        """
        filtered = self._debounce.process(raw, now)
        return filtered, not filtered

