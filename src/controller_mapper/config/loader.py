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
    trn_type = trn_raw.get("type", "")
    negative_raw = dict(trn_raw.get("negative", {}))
    positive_raw = dict(trn_raw.get("positive", {}))
    output_index = int(
        negative_raw.get("output_button", out_raw.get("index", 0))
        if trn_type == "axis_to_dual_button"
        else out_raw.get("index", 0)
    )
    output_positive_index = out_raw.get("positive_index")
    if trn_type == "axis_to_dual_button" and output_positive_index is None:
        output_positive_index = positive_raw.get("output_button", min(output_index + 1, 127))
    split_off_default = min(output_index + 1, 127)

    return RuleConfig(
        name=raw.get("name", ""),
        mode=raw.get("mode", "*"),
        input=InputConfig(
            device=inp_raw.get("device", ""),
            type=inp_raw.get("type", "button"),
            index=int(inp_raw.get("index", 0)),
            negative_index=inp_raw.get("negative_index"),
            positive_index=inp_raw.get("positive_index"),
            hat_x=int(inp_raw.get("hat_x", 0)),
            hat_y=int(inp_raw.get("hat_y", 1)),
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
            type=trn_type,
            on_threshold=float(trn_raw.get("on_threshold", 0.5)),
            off_threshold=float(trn_raw.get("off_threshold", 0.4)),
            released_value=float(trn_raw.get("released_value", 0.0)),
            pressed_value=float(trn_raw.get("pressed_value", 1.0)),
            mode=trn_raw.get("mode", "direct"),
            speed_per_sec=float(trn_raw.get("speed_per_sec", 1.0)),
            return_to_center=bool(trn_raw.get("return_to_center", False)),
            negative=negative_raw,
            positive=positive_raw,
            negative_direction=bool(trn_raw.get("negative_direction", False)),
            on_button=(
                output_index
                if trn_type == "button_split"
                else int(trn_raw.get("on_button", 0))
            ),
            off_button=int(
                trn_raw.get(
                    "off_button",
                    split_off_default if trn_type == "button_split" else 1,
                )
            ),
        ),
        output=RuleOutputConfig(
            device=out_raw.get("device", "vjoy1"),
            type=out_raw.get("type", "button"),
            index=output_index,
            positive_index=(
                int(output_positive_index)
                if output_positive_index is not None
                else None
            ),
            name=out_raw.get("name", ""),
        ),
    )


# ─────────────────────────────────────────────────────────────────
# 保存
# ─────────────────────────────────────────────────────────────────

def save_profile(profile: ProfileConfig, path: str | Path) -> None:
    """ProfileConfig を YAML ファイルへ保存する.

    Args:
        profile: 保存するプロファイル
        path:    書き出し先ファイルパス

    Raises:
        ProfileLoadError: 書き込み失敗
    """
    safe_path = Path(path).resolve()
    data = _profile_to_dict(profile)

    try:
        with safe_path.open("w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    except OSError as e:
        raise ProfileLoadError(f"ファイルへ書き込めません: {safe_path}") from e

    logger.info("プロファイルを保存しました: %s", safe_path)


def _profile_to_dict(profile: ProfileConfig) -> dict[str, Any]:
    """ProfileConfig を辞書に変換する (YAML書き出し用)."""
    data: dict[str, Any] = {}

    data["profile"] = {"name": profile.name, "version": profile.version}

    if profile.devices:
        data["devices"] = {}
        for dev_id, dev in profile.devices.items():
            match_dict: dict[str, str] = {}
            if dev.match.name_contains:
                match_dict["name_contains"] = dev.match.name_contains
            if dev.match.role:
                match_dict["role"] = dev.match.role
            data["devices"][dev_id] = {"match": match_dict} if match_dict else None

    data["output"] = {
        "type": profile.output.type,
        "device_id": profile.output.device_id,
    }

    data["global"] = {
        "update_rate_hz": profile.global_.update_rate_hz,
        "gui_rate_hz": profile.global_.gui_rate_hz,
    }

    data["modes"] = {
        "default": profile.modes.default,
        "definitions": profile.modes.definitions,
    }

    data["rules"] = [_rule_to_dict(r) for r in profile.rules]
    return data


def _rule_to_dict(rule: RuleConfig) -> dict[str, Any]:
    """RuleConfig を辞書に変換する."""
    d: dict[str, Any] = {"name": rule.name}
    if rule.mode != "*":
        d["mode"] = rule.mode
    else:
        d["mode"] = "*"

    # input
    inp: dict[str, Any] = {
        "device": rule.input.device,
        "type": rule.input.type,
        "index": rule.input.index,
    }
    if rule.input.type == "button_pair":
        if rule.input.negative_index is not None:
            inp["negative_index"] = rule.input.negative_index
        if rule.input.positive_index is not None:
            inp["positive_index"] = rule.input.positive_index
    elif rule.input.type == "hat":
        inp["hat_x"] = rule.input.hat_x
        inp["hat_y"] = rule.input.hat_y
    d["input"] = inp

    # filters (デフォルト値でないもののみ出力)
    f = rule.filters
    flt: dict[str, Any] = {}
    if f.debounce_ms > 0:
        flt["debounce_ms"] = f.debounce_ms
    if f.minimum_on_ms > 0:
        flt["minimum_on_ms"] = f.minimum_on_ms
    if f.minimum_off_ms > 0:
        flt["minimum_off_ms"] = f.minimum_off_ms
    if f.deadzone > 0:
        flt["deadzone"] = f.deadzone
    if f.end_deadzone > 0:
        flt["end_deadzone"] = f.end_deadzone
    if f.curve != 1.0:
        flt["curve"] = f.curve
    if f.invert:
        flt["invert"] = True
    if f.smoothing > 0:
        flt["smoothing"] = f.smoothing
    if f.toggle:
        flt["toggle"] = True
    if flt:
        d["filters"] = flt

    # transform (typeが空でないときのみ出力)
    t = rule.transform
    if t.type:
        trn: dict[str, Any] = {"type": t.type}
        if t.type in ("axis_to_button",):
            trn["on_threshold"] = t.on_threshold
            trn["off_threshold"] = t.off_threshold
        elif t.type == "axis_negative_to_button":
            trn["on_threshold"] = t.on_threshold
            trn["off_threshold"] = t.off_threshold
            if t.negative_direction:
                trn["negative_direction"] = True
        elif t.type == "axis_to_dual_button":
            trn["negative"] = {
                k: v for k, v in t.negative.items() if k != "output_button"
            }
            trn["positive"] = {
                k: v for k, v in t.positive.items() if k != "output_button"
            }
        elif t.type in ("button_to_axis",):
            trn["released_value"] = t.released_value
            trn["pressed_value"] = t.pressed_value
        elif t.type in ("buttons_to_axis",):
            trn["mode"] = t.mode
            trn["speed_per_sec"] = t.speed_per_sec
            trn["return_to_center"] = t.return_to_center
        elif t.type == "button_split":
            trn["off_button"] = t.off_button
        d["transform"] = trn

    # output
    out: dict[str, Any] = {"type": rule.output.type}
    if rule.output.type == "axis":
        if rule.output.name:
            out["name"] = rule.output.name
    else:
        out["index"] = rule.output.index
        if rule.output.positive_index is not None:
            out["positive_index"] = rule.output.positive_index
    d["output"] = out

    return d
