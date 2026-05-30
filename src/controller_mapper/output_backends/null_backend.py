"""出力バックエンド: Null (デモ・テスト用).

何もしない出力バックエンド.
vJoyが使えない環境 (Linux / vJoy未インストール) で使用する.
"""
from __future__ import annotations

import logging

from controller_mapper.core.state import OutputState
from controller_mapper.output_backends.base import OutputBackend

logger = logging.getLogger(__name__)


class NullBackend(OutputBackend):
    """何もしない出力バックエンド."""

    def __init__(self) -> None:
        self._connected = False

    @property
    def backend_name(self) -> str:
        return "null"

    @property
    def is_connected(self) -> bool:
        return self._connected

    def initialize(self) -> None:
        self._connected = True
        logger.info("NullBackend 初期化 (出力なし)")

    def shutdown(self) -> None:
        self._connected = False

    def write(self, state: OutputState) -> None:
        pass  # 意図的に何もしない
