"""アプリ設定の読み書き.

~/.controller_mapper/settings.yaml にアプリ起動設定を保持する.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_SETTINGS_DIR = Path.home() / ".controller_mapper"
_SETTINGS_FILE = _SETTINGS_DIR / "settings.yaml"


@dataclass
class AppSettings:
    """アプリ起動設定."""
    default_profile: str = ""     # デフォルトプロファイルのパス (空=なし)
    auto_start: bool = False      # 起動時にパイプラインを自動開始するか


def load_settings() -> AppSettings:
    """設定ファイルを読み込む. ファイルがなければデフォルト値を返す."""
    if not _SETTINGS_FILE.exists():
        logger.debug("設定ファイルなし: デフォルト値を使用")
        return AppSettings()

    try:
        with _SETTINGS_FILE.open(encoding="utf-8") as f:
            raw: dict[str, Any] = yaml.safe_load(f) or {}
        settings = AppSettings(
            default_profile=str(raw.get("default_profile", "")),
            auto_start=bool(raw.get("auto_start", False)),
        )
        logger.info("設定読み込み: %s", _SETTINGS_FILE)
        return settings
    except Exception as e:
        logger.warning("設定読み込みエラー (デフォルト値を使用): %s", e)
        return AppSettings()


def save_settings(settings: AppSettings) -> None:
    """設定ファイルを書き出す."""
    _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "default_profile": settings.default_profile,
        "auto_start": settings.auto_start,
    }
    try:
        with _SETTINGS_FILE.open("w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        logger.info("設定保存: %s", _SETTINGS_FILE)
    except Exception as e:
        logger.error("設定保存エラー: %s", e)


def settings_file_path() -> Path:
    """設定ファイルのパスを返す."""
    return _SETTINGS_FILE
