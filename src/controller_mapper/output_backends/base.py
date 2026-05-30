"""出力バックエンド基底クラス."""
from __future__ import annotations

from abc import ABC, abstractmethod

from controller_mapper.core.state import OutputState


class OutputBackend(ABC):
    """出力バックエンドの抽象基底クラス."""

    @abstractmethod
    def initialize(self) -> None:
        """バックエンドを初期化する."""

    @abstractmethod
    def shutdown(self) -> None:
        """バックエンドを終了する."""

    @abstractmethod
    def write(self, state: OutputState) -> None:
        """OutputState を仮想デバイスへ書き込む."""

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """バックエンド名を返す."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """接続状態を返す."""
