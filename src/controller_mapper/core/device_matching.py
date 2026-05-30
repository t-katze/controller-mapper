"""プロファイルの論理デバイス名を実入力デバイスへ割り当てる."""
from __future__ import annotations

import logging
import re

from controller_mapper.config.schema import DeviceConfig, ProfileConfig
from controller_mapper.core.state import DeviceInfo

logger = logging.getLogger(__name__)

_ROLE_KEYWORDS = {
    "stick": ("stick", "joystick", "flight stick"),
    "throttle": ("throttle",),
    "rudder": ("rudder", "pedal", "pedals"),
    "pedal": ("pedal", "pedals", "rudder"),
    "pedals": ("pedal", "pedals", "rudder"),
}


def _normalize_match_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _role_keywords(role: str) -> tuple[str, ...]:
    normalized = role.strip().lower()
    if not normalized:
        return ()
    return _ROLE_KEYWORDS.get(normalized, (normalized,))


def score_device_match(config: DeviceConfig, device: DeviceInfo) -> int | None:
    """デバイスがプロファイル条件に合う場合はスコア、合わない場合はNoneを返す."""
    name = device.name.lower()
    normalized_name = _normalize_match_text(device.name)
    needle = config.match.name_contains.strip().lower()
    normalized_needle = _normalize_match_text(needle)
    role = config.match.role.strip().lower()

    if normalized_needle and normalized_needle not in normalized_name:
        return None

    score = 0
    if needle:
        score += 100 + len(needle)

    keywords = _role_keywords(role)
    if keywords:
        if any(keyword in name for keyword in keywords):
            score += 50
        else:
            score -= 10

    return score


def resolve_device_aliases(
    profile: ProfileConfig,
    devices: list[DeviceInfo],
) -> dict[str, str]:
    """プロファイル上の論理デバイス名 -> 実デバイスID の対応を作る."""
    aliases: dict[str, str] = {}
    used_device_ids: set[str] = set()

    for logical_name, config in profile.devices.items():
        direct = next((dev for dev in devices if dev.device_id == logical_name), None)
        if direct is not None:
            aliases[logical_name] = direct.device_id
            used_device_ids.add(direct.device_id)
            logger.info(
                "プロファイルデバイス '%s' -> %s (%s)",
                logical_name,
                direct.device_id,
                direct.name,
            )
            continue

        candidates: list[tuple[int, int, DeviceInfo]] = []
        for index, dev in enumerate(devices):
            if dev.device_id in used_device_ids:
                continue
            score = score_device_match(config, dev)
            if score is not None:
                candidates.append((score, index, dev))

        if not candidates:
            for index, dev in enumerate(devices):
                score = score_device_match(config, dev)
                if score is not None:
                    candidates.append((score, index, dev))

        if candidates:
            candidates.sort(key=lambda item: (-item[0], item[1]))
            _, _, matched = candidates[0]
            aliases[logical_name] = matched.device_id
            used_device_ids.add(matched.device_id)
            logger.info(
                "プロファイルデバイス '%s' -> %s (%s)",
                logical_name,
                matched.device_id,
                matched.name,
            )
        else:
            logger.warning(
                "プロファイルデバイス '%s' に一致する入力デバイスがありません",
                logical_name,
            )

    return aliases