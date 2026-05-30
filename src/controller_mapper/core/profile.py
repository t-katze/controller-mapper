"""プロファイル管理 (core層の薄いラッパー)."""
from __future__ import annotations

from pathlib import Path

from controller_mapper.config.loader import load_profile
from controller_mapper.config.schema import ProfileConfig


def load(path: str | Path) -> ProfileConfig:
    """YAMLプロファイルを読み込んで返す."""
    return load_profile(path)
