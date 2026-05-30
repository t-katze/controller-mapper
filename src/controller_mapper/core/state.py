"""内部データ構造の定義.

設計書 §8 に対応.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DeviceState:
    """1デバイス分の入力状態.

    axes:    軸インデックス → 値 (-1.0 〜 1.0)
    buttons: ボタンインデックス → ON/OFF
    hats:    Hatインデックス → (x, y) タプル (-1/0/1)
    """

    axes: dict[int, float] = field(default_factory=dict)
    buttons: dict[int, bool] = field(default_factory=dict)
    hats: dict[int, tuple[int, int]] = field(default_factory=dict)

    def copy(self) -> "DeviceState":
        return DeviceState(
            axes=dict(self.axes),
            buttons=dict(self.buttons),
            hats=dict(self.hats),
        )


@dataclass
class InputState:
    """生入力状態 (Filter前).

    timestamp: モノトニック時刻 (秒)
    devices:   デバイスID → DeviceState
    """

    timestamp: float = 0.0
    devices: dict[str, DeviceState] = field(default_factory=dict)


@dataclass
class FilteredState:
    """フィルタ後の状態.

    同じ構造だが明示的に区別する.
    """

    timestamp: float = 0.0
    devices: dict[str, DeviceState] = field(default_factory=dict)


@dataclass
class OutputState:
    """仮想デバイスへ出力する状態.

    axes:    軸名 → 値 (0.0 〜 1.0 の場合もあるため float)
    buttons: ボタンインデックス → ON/OFF
    hats:    Hatインデックス → (x, y) タプル
    """

    axes: dict[str, float] = field(default_factory=dict)
    buttons: dict[int, bool] = field(default_factory=dict)
    hats: dict[int, tuple[int, int]] = field(default_factory=dict)


@dataclass
class DeviceInfo:
    """検出デバイスのメタ情報."""

    device_id: str
    name: str
    num_axes: int
    num_buttons: int
    num_hats: int
    backend_name: str
    guid: str = ""
