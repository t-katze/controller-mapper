"""入力バックエンド基底クラス."""
from __future__ import annotations

from abc import ABC, abstractmethod

from controller_mapper.core.state import DeviceInfo, DeviceState


class InputBackend(ABC):
    """入力バックエンドの抽象基底クラス."""

    @abstractmethod
    def initialize(self) -> None:
        """バックエンドを初期化する."""

    @abstractmethod
    def shutdown(self) -> None:
        """バックエンドを終了する."""

    @abstractmethod
    def get_devices(self) -> list[DeviceInfo]:
        """接続済みデバイスの一覧を返す."""

    @abstractmethod
    def poll(self) -> dict[str, DeviceState]:
        """すべてのデバイスの現在状態を返す."""

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """バックエンド名を返す."""
