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
