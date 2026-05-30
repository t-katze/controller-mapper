"""モード・レイヤー管理.

設計書 §6 に対応.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ModeManager:
    """現在のモードを管理するクラス.

    Args:
        definitions: 有効なモード名のリスト
        default:     初期モード名
    """

    def __init__(self, definitions: list[str], default: str = "default") -> None:
        self._modes = list(definitions) if definitions else ["default"]
        self._current = default if default in self._modes else self._modes[0]
        logger.info("ModeManager 初期化: モード=%s, 初期=%s", self._modes, self._current)

    @property
    def current(self) -> str:
        return self._current

    def cycle(self) -> str:
        """次のモードに循環して切り替える."""
        idx = self._modes.index(self._current)
        self._current = self._modes[(idx + 1) % len(self._modes)]
        logger.info("モード切替: %s", self._current)
        return self._current

    def set_mode(self, name: str) -> None:
        """指定モードに直接切り替える."""
        if name not in self._modes:
            logger.warning("不明なモード: %s (現在: %s)", name, self._current)
            return
        self._current = name
        logger.info("モード設定: %s", self._current)

    def matches(self, rule_mode: str) -> bool:
        """ルールのmode指定が現在のモードに一致するか判定する.

        rule_mode が "*" のときは常にTrue.
        """
        return rule_mode == "*" or rule_mode == self._current
