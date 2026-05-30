"""YAMLプロファイルのロード.

セキュリティ: yaml.safe_load() を使用し任意コード実行を防止する.
ファイルパスは pathlib.Path で処理しパストラバーサルを防止する.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from controller_mapper.config.schema import (
    DeviceConfig,
    DeviceMatchConfig,
    FiltersConfig,
    GlobalConfig,
    InputConfig,
    ModesConfig,
    OutputConfig,
    ProfileConfig,
    RuleConfig,
    RuleOutputConfig,
    TransformConfig,
)
from controller_mapper.config.validator import validate_profile
from controller_mapper.core.errors import ProfileLoadError, ProfileValidationError

logger = logging.getLogger(__name__)


def load_profile(path: str | Path) -> ProfileConfig:
    """YAMLファイルからプロファイルを読み込む.

    Args:
        path: YAMLファイルパス

    Returns:
        ProfileConfig インスタンス

    Raises:
        ProfileLoadError: ファイル読み込み失敗
        ProfileValidationError: スキーマ不正
    """
    # セキュリティ: pathlib.Path で正規化
    safe_path = Path(path).resolve()
    logger.info("プロファイル読み込み: %s", safe_path)

    try:
        with safe_path.open(encoding="utf-8") as f:
            # セキュリティ: safe_load で任意コード実行を防止
            raw: dict[str, Any] = yaml.safe_load(f) or {}
    except OSError as e:
        raise ProfileLoadError(f"ファイルを開けません: {safe_path}") from e
    except yaml.YAMLError as e:
        raise ProfileLoadError(f"YAML解析エラー: {e}") from e

    try:
        profile = _parse_profile(raw)
    except (KeyError, TypeError, ValueError) as e:
        raise ProfileLoadError(f"プロファイル変換エラー: {e}") from e

    try:
        validate_profile(profile)
    except ProfileValidationError:
        raise

    logger.info("プロファイル '%s' を正常に読み込みました (ルール数: %d)", profile.name, len(profile.rules))
    return profile


def _parse_profile(raw: dict[str, Any]) -> ProfileConfig:
    p = raw.get("profile", {})
    profile = ProfileConfig(
        name=p.get("name", "default"),
        version=int(p.get("version", 1)),
    )

    # devices
    for dev_id, dev_raw in (raw.get("devices") or {}).items():
        match_raw = dev_raw.get("match", {}) if dev_raw else {}
        profile.devices[dev_id] = DeviceConfig(
            match=DeviceMatchConfig(
                name_contains=match_raw.get("name_contains", ""),
                role=match_raw.get("role", ""),
            )
        )

    # output
    out_raw = raw.get("output", {})
    profile.output = OutputConfig(
        type=out_raw.get("type", "null"),
        device_id=int(out_raw.get("device_id", 1)),
    )

    # global
    glob_raw = raw.get("global", {})
    profile.global_ = GlobalConfig(
        update_rate_hz=int(glob_raw.get("update_rate_hz", 500)),
        gui_rate_hz=int(glob_raw.get("gui_rate_hz", 30)),
    )

    # modes
    modes_raw = raw.get("modes", {})
    profile.modes = ModesConfig(
        default=modes_raw.get("default", "default"),
        definitions=list(modes_raw.get("definitions", ["default"])),
    )

    # rules
    for rule_raw in (raw.get("rules") or []):
        profile.rules.append(_parse_rule(rule_raw))

    return profile


def _parse_rule(raw: dict[str, Any]) -> RuleConfig:
    inp_raw = raw.get("input", {})
    flt_raw = raw.get("filters", {})
    trn_raw = raw.get("transform", {})
    out_raw = raw.get("output", {})

    return RuleConfig(
        name=raw.get("name", ""),
        mode=raw.get("mode", "*"),
        input=InputConfig(
            device=inp_raw.get("device", ""),
            type=inp_raw.get("type", "button"),
            index=int(inp_raw.get("index", 0)),
            negative_index=inp_raw.get("negative_index"),
            positive_index=inp_raw.get("positive_index"),
        ),
        filters=FiltersConfig(
            debounce_ms=float(flt_raw.get("debounce_ms", 0.0)),
            minimum_on_ms=float(flt_raw.get("minimum_on_ms", 0.0)),
            minimum_off_ms=float(flt_raw.get("minimum_off_ms", 0.0)),
            deadzone=float(flt_raw.get("deadzone", 0.0)),
            end_deadzone=float(flt_raw.get("end_deadzone", 0.0)),
            curve=float(flt_raw.get("curve", 1.0)),
            invert=bool(flt_raw.get("invert", False)),
            smoothing=float(flt_raw.get("smoothing", 0.0)),
            toggle=bool(flt_raw.get("toggle", False)),
        ),
        transform=TransformConfig(
            type=trn_raw.get("type", ""),
            on_threshold=float(trn_raw.get("on_threshold", 0.5)),
            off_threshold=float(trn_raw.get("off_threshold", 0.4)),
            released_value=float(trn_raw.get("released_value", 0.0)),
            pressed_value=float(trn_raw.get("pressed_value", 1.0)),
            mode=trn_raw.get("mode", "direct"),
            speed_per_sec=float(trn_raw.get("speed_per_sec", 1.0)),
            return_to_center=bool(trn_raw.get("return_to_center", False)),
            negative=dict(trn_raw.get("negative", {})),
            positive=dict(trn_raw.get("positive", {})),
        ),
        output=RuleOutputConfig(
            device=out_raw.get("device", "vjoy1"),
            type=out_raw.get("type", "button"),
            index=int(out_raw.get("index", 0)),
            name=out_raw.get("name", ""),
        ),
    )
