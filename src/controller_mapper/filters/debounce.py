"""フィルタ: デバウンス・エッジ検出・トグル.

設計書 §4.3 に対応.
"""
from __future__ import annotations

import time


class DebounceFilter:
    """ボタンノイズ除去フィルタ.

    Args:
        debounce_ms:    状態が安定するまでの待ち時間 [ms]
        minimum_on_ms:  最小ON持続時間 [ms]  これより短いONは無視
        minimum_off_ms: 最小OFF持続時間 [ms]  これより短いOFF抜けは無視
        toggle:         Trueにすると押すたびにON/OFF反転
    """

    def __init__(
        self,
        debounce_ms: float = 30.0,
        minimum_on_ms: float = 20.0,
        minimum_off_ms: float = 20.0,
        toggle: bool = False,
    ) -> None:
        self.debounce_ms = debounce_ms
        self.minimum_on_ms = minimum_on_ms
        self.minimum_off_ms = minimum_off_ms
        self.toggle = toggle

        self._confirmed: bool = False          # 確定済み出力状態
        self._pending: bool = False            # 保留中の候補状態
        self._pending_since: float = 0.0       # 候補に変わった時刻
        self._on_since: float | None = None    # 現在ONになった時刻
        self._off_since: float | None = None   # 現在OFFになった時刻
        self._toggle_state: bool = False       # トグル状態

    def process(self, raw: bool, now: float | None = None) -> bool:
        """生ボタン値を受け取りフィルタ後の値を返す.

        処理フロー:
          1. 入力が変化したら pending をリセット
          2. debounce_ms 安定しなければ旧出力を返す
          3. デバウンス完了後、minimum_on/off_ms を待ってから状態確定

        Args:
            raw: 生ボタン状態
            now: 現在時刻 [秒]. Noneのとき time.monotonic() を使う.

        Returns:
            フィルタ後のボタン状態
        """
        t = now if now is not None else time.monotonic()

        # 状態変化を検出して保留タイマーをリセット
        if raw != self._pending:
            self._pending = raw
            self._pending_since = t
            self._on_since = None
            self._off_since = None

        # デバウンス: pendingが安定期間を超えるまで旧出力を返す
        elapsed_ms = (t - self._pending_since) * 1000.0
        if elapsed_ms < self.debounce_ms:
            return self._get_output()

        candidate = self._pending

        if candidate:
            # 最小ON時間: pending_since から計測 (デバウンス期間と重複してカウント)
            if self._on_since is None:
                self._on_since = self._pending_since
            on_ms = (t - self._on_since) * 1000.0
            if on_ms < self.minimum_on_ms:
                return self._get_output()
        else:
            # 最小OFF時間: pending_since から計測
            if self._off_since is None:
                self._off_since = self._pending_since
                self._on_since = None
            off_ms = (t - self._off_since) * 1000.0
            if off_ms < self.minimum_off_ms:
                return self._get_output()

        # 状態確定
        if candidate != self._confirmed:
            self._confirmed = candidate
            if self.toggle and candidate:
                self._toggle_state = not self._toggle_state

        return self._get_output()

    def _get_output(self) -> bool:
        if self.toggle:
            return self._toggle_state
        return self._confirmed

    def reset(self) -> None:
        """内部状態をリセットする."""
        self.__init__(  # type: ignore[misc]
            self.debounce_ms,
            self.minimum_on_ms,
            self.minimum_off_ms,
            self.toggle,
        )
