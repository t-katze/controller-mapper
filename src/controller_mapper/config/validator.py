"""プロファイルバリデーション."""
from __future__ import annotations

import logging
from controller_mapper.config.schema import ProfileConfig, RuleConfig
from controller_mapper.core.errors import ProfileValidationError

logger = logging.getLogger(__name__)


def validate_profile(profile: ProfileConfig) -> None:
    """プロファイル全体を検証する.

    不正な値があれば ProfileValidationError を送出する.
    """
    if not profile.name:
        raise ProfileValidationError("profile.name が空です")

    for i, rule in enumerate(profile.rules):
        _validate_rule(i, rule)


def _validate_rule(index: int, rule: RuleConfig) -> None:
    if not rule.name:
        raise ProfileValidationError(f"rules[{index}].name が空です")
    if not rule.input.device:
        raise ProfileValidationError(f"rules[{index}] ({rule.name}): input.device が空です")

    filters = rule.filters
    if filters.debounce_ms < 0:
        raise ProfileValidationError(f"rules[{index}] ({rule.name}): debounce_ms < 0")
    if not (0.0 <= filters.deadzone <= 1.0):
        raise ProfileValidationError(f"rules[{index}] ({rule.name}): deadzone は 0〜1 で指定してください")
    if filters.curve <= 0:
        raise ProfileValidationError(f"rules[{index}] ({rule.name}): curve は正の値で指定してください")

    transform = rule.transform
    if transform.type in ("axis_to_button", "axis_to_dual_button"):
        if transform.on_threshold <= transform.off_threshold:
            logger.warning(
                "rules[%d] (%s): on_threshold <= off_threshold はヒステリシスが効きません",
                index,
                rule.name,
            )
