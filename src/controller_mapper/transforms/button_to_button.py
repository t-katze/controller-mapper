"""変換: button → button.

設計書 §5.1 に対応.
"""
from __future__ import annotations

import time

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
        gap_ms: 切替時に両方の出力ボタンを同時OFFにする時間 (ms)
    """

    def __init__(self, on_button: int = 0, off_button: int = 1,
                 debounce_ms: float = 0.0,
                 gap_ms: float = 0.0) -> None:
        self.on_button = on_button
        self.off_button = off_button
        self.gap_ms = gap_ms
        self.filtered = False
        self._debounce = DebounceFilter(
            debounce_ms=debounce_ms,
            minimum_on_ms=0.0,
            minimum_off_ms=0.0,
        )
        self._last_filtered: bool | None = None
        self._gap_until = 0.0
        self._gap_active = False

    def process(self, raw: bool, now: float | None = None) -> tuple[bool, bool]:
        """(on_buttonの状態, off_buttonの状態) を返す.

        物理ボタンが ON → on_button=True,  off_button=False
        物理ボタンが OFF → on_button=False, off_button=True
        """
        t = now if now is not None else time.monotonic()
        filtered = self._debounce.process(raw, t)
        self.filtered = filtered

        on_result = filtered
        off_result = not filtered
        gap_s = max(0.0, self.gap_ms) / 1000.0

        if self._last_filtered is None:
            self._last_filtered = filtered
            return on_result, off_result

        if gap_s <= 0.0:
            self._last_filtered = filtered
            self._gap_active = False
            return on_result, off_result

        if filtered != self._last_filtered:
            self._gap_active = True
            self._gap_until = t + gap_s
            self._last_filtered = filtered

        if self._gap_active and t < self._gap_until:
            return False, False

        self._gap_active = False

        return on_result, off_result


class ButtonOffTransform:
    """物理ボタンがOFFのときだけ仮想ボタンを押す."""

    def __init__(self, debounce_ms: float = 0.0) -> None:
        self._debounce = DebounceFilter(
            debounce_ms=debounce_ms,
            minimum_on_ms=0.0,
            minimum_off_ms=0.0,
        )

    def process(self, raw: bool, now: float | None = None) -> bool:
        filtered = self._debounce.process(raw, now)
        return not filtered
