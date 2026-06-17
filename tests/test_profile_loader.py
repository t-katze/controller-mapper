"""プロファイル読み込み・バリデーションのテスト.

設計書 §11, §14 テスト方針 に対応.
"""
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from controller_mapper.config.loader import load_profile, save_profile
from controller_mapper.config.schema import (
    InputConfig,
    ProfileConfig,
    RuleConfig,
    RuleOutputConfig,
    TransformConfig,
)
from controller_mapper.core.errors import ProfileLoadError, ProfileValidationError


def _write_yaml(tmp_dir: Path, content: dict, filename: str = "test.yaml") -> Path:
    """一時ディレクトリにYAMLファイルを書き出す."""
    path = tmp_dir / filename
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(content, f, allow_unicode=True)
    return path


class TestProfileLoader:
    """load_profile の単体テスト."""

    def test_minimal_profile(self, tmp_path: Path) -> None:
        """最小構成のプロファイルが読み込めること."""
        data = {
            "profile": {"name": "test", "version": 1},
            "rules": [],
        }
        path = _write_yaml(tmp_path, data)
        profile = load_profile(path)
        assert profile.name == "test"
        assert profile.version == 1
        assert len(profile.rules) == 0

    def test_profile_with_devices(self, tmp_path: Path) -> None:
        """devices セクションが正しくパースされること."""
        data = {
            "profile": {"name": "dev_test", "version": 1},
            "devices": {
                "my_stick": {"match": {"name_contains": "X56", "role": "stick"}},
            },
            "rules": [],
        }
        path = _write_yaml(tmp_path, data)
        profile = load_profile(path)
        assert "my_stick" in profile.devices
        assert profile.devices["my_stick"].match.name_contains == "X56"
        assert profile.devices["my_stick"].match.role == "stick"

    def test_profile_with_rules(self, tmp_path: Path) -> None:
        """ルールが正しくパースされること."""
        data = {
            "profile": {"name": "rule_test", "version": 1},
            "rules": [
                {
                    "name": "roll",
                    "mode": "*",
                    "input": {"device": "stick", "type": "axis", "index": 0},
                    "filters": {"deadzone": 0.03, "curve": 1.3},
                    "output": {"type": "axis", "name": "x"},
                }
            ],
        }
        path = _write_yaml(tmp_path, data)
        profile = load_profile(path)
        assert len(profile.rules) == 1
        rule = profile.rules[0]
        assert rule.name == "roll"
        assert rule.input.device == "stick"
        assert rule.input.type == "axis"
        assert rule.input.index == 0
        assert rule.filters.deadzone == pytest.approx(0.03)
        assert rule.filters.curve == pytest.approx(1.3)
        assert rule.output.name == "x"

    def test_profile_with_output_config(self, tmp_path: Path) -> None:
        """output セクションが正しくパースされること."""
        data = {
            "profile": {"name": "out_test", "version": 1},
            "output": {"type": "vjoy", "device_id": 2},
            "rules": [],
        }
        path = _write_yaml(tmp_path, data)
        profile = load_profile(path)
        assert profile.output.type == "vjoy"
        assert profile.output.device_id == 2

    def test_profile_with_modes(self, tmp_path: Path) -> None:
        """modes セクションが正しくパースされること."""
        data = {
            "profile": {"name": "mode_test", "version": 1},
            "modes": {"default": "nav", "definitions": ["nav", "aa", "ag"]},
            "rules": [],
        }
        path = _write_yaml(tmp_path, data)
        profile = load_profile(path)
        assert profile.modes.default == "nav"
        assert profile.modes.definitions == ["nav", "aa", "ag"]

    def test_profile_with_global_config(self, tmp_path: Path) -> None:
        """global セクションが正しくパースされること."""
        data = {
            "profile": {"name": "glob_test", "version": 1},
            "global": {"update_rate_hz": 1000, "gui_rate_hz": 60},
            "rules": [],
        }
        path = _write_yaml(tmp_path, data)
        profile = load_profile(path)
        assert profile.global_.update_rate_hz == 1000
        assert profile.global_.gui_rate_hz == 60

    def test_transform_axis_to_button(self, tmp_path: Path) -> None:
        """axis_to_button 変換のパースが正しいこと."""
        data = {
            "profile": {"name": "transform_test", "version": 1},
            "rules": [
                {
                    "name": "slider_brake",
                    "input": {"device": "stick", "type": "axis", "index": 3},
                    "transform": {
                        "type": "axis_to_button",
                        "on_threshold": 0.65,
                        "off_threshold": 0.50,
                    },
                    "output": {"type": "button", "index": 20},
                }
            ],
        }
        path = _write_yaml(tmp_path, data)
        profile = load_profile(path)
        rule = profile.rules[0]
        assert rule.transform.type == "axis_to_button"
        assert rule.transform.on_threshold == pytest.approx(0.65)
        assert rule.transform.off_threshold == pytest.approx(0.50)

    def test_transform_button_split_uses_output_index_as_on_button(
        self, tmp_path: Path
    ) -> None:
        """button_split は output.index をON側ボタンとして扱うこと."""
        data = {
            "profile": {"name": "split_test", "version": 1},
            "rules": [
                {
                    "name": "split",
                    "input": {"device": "stick", "type": "button", "index": 0},
                    "transform": {
                        "type": "button_split",
                        "off_button": 11,
                        "gap_ms": 75,
                    },
                    "output": {"type": "button", "index": 10},
                }
            ],
        }
        path = _write_yaml(tmp_path, data)
        profile = load_profile(path)
        rule = profile.rules[0]
        assert rule.output.index == 10
        assert rule.transform.on_button == 10
        assert rule.transform.off_button == 11
        assert rule.transform.gap_ms == pytest.approx(75)

    def test_save_button_split_does_not_write_on_button(self, tmp_path: Path) -> None:
        """button_split のON側ボタンは output.index にだけ保存すること."""
        profile = ProfileConfig(name="save_split")
        profile.rules.append(
            RuleConfig(
                name="split",
                input=InputConfig(device="stick", type="button", index=0),
                transform=TransformConfig(
                    type="button_split",
                    on_button=10,
                    off_button=11,
                    gap_ms=25,
                ),
                output=RuleOutputConfig(type="button", index=10),
            )
        )
        path = tmp_path / "saved.yaml"

        save_profile(profile, path)

        saved = yaml.safe_load(path.read_text(encoding="utf-8"))
        transform = saved["rules"][0]["transform"]
        assert "on_button" not in transform
        assert transform["off_button"] == 11
        assert transform["gap_ms"] == 25
        assert saved["rules"][0]["output"]["index"] == 10

    def test_transform_button_off_uses_output_index(self, tmp_path: Path) -> None:
        """button_off は output.index をOFF側ボタンとして扱うこと."""
        data = {
            "profile": {"name": "button_off_test", "version": 1},
            "rules": [
                {
                    "name": "off_only",
                    "input": {"device": "stick", "type": "button", "index": 0},
                    "transform": {"type": "button_off"},
                    "output": {"type": "button", "index": 12},
                }
            ],
        }
        path = _write_yaml(tmp_path, data)
        profile = load_profile(path)
        rule = profile.rules[0]
        assert rule.transform.type == "button_off"
        assert rule.output.index == 12

    def test_save_button_off_writes_only_type(self, tmp_path: Path) -> None:
        """button_off は追加パラメータなしで保存すること."""
        profile = ProfileConfig(name="save_button_off")
        profile.rules.append(
            RuleConfig(
                name="off_only",
                input=InputConfig(device="stick", type="button", index=0),
                transform=TransformConfig(type="button_off"),
                output=RuleOutputConfig(type="button", index=12),
            )
        )
        path = tmp_path / "saved_button_off.yaml"

        save_profile(profile, path)

        saved = yaml.safe_load(path.read_text(encoding="utf-8"))
        rule = saved["rules"][0]
        assert rule["transform"] == {"type": "button_off"}
        assert rule["output"]["index"] == 12

    def test_hat_input_direction_is_parsed(self, tmp_path: Path) -> None:
        """hat 入力は Hat 番号と方向を保持して読み込めること."""
        data = {
            "profile": {"name": "hat_test", "version": 1},
            "rules": [
                {
                    "name": "pov_up",
                    "input": {
                        "device": "stick",
                        "type": "hat",
                        "index": 0,
                        "hat_x": 0,
                        "hat_y": 1,
                    },
                    "output": {"type": "button", "index": 12},
                }
            ],
        }
        path = _write_yaml(tmp_path, data)
        profile = load_profile(path)
        rule = profile.rules[0]

        assert rule.input.type == "hat"
        assert rule.input.index == 0
        assert rule.input.hat_x == 0
        assert rule.input.hat_y == 1

    def test_save_hat_input_writes_direction(self, tmp_path: Path) -> None:
        """hat 入力は方向をYAMLへ保存すること."""
        profile = ProfileConfig(name="save_hat")
        profile.rules.append(
            RuleConfig(
                name="pov_right",
                input=InputConfig(
                    device="stick",
                    type="hat",
                    index=0,
                    hat_x=1,
                    hat_y=0,
                ),
                output=RuleOutputConfig(type="button", index=12),
            )
        )
        path = tmp_path / "saved_hat.yaml"

        save_profile(profile, path)

        saved = yaml.safe_load(path.read_text(encoding="utf-8"))
        inp = saved["rules"][0]["input"]
        assert inp["type"] == "hat"
        assert inp["hat_x"] == 1
        assert inp["hat_y"] == 0

    def test_transform_axis_to_dual_uses_output_indices(
        self, tmp_path: Path
    ) -> None:
        """axis_to_dual_button は出力欄で2つのボタンを指定できること."""
        data = {
            "profile": {"name": "dual_test", "version": 1},
            "rules": [
                {
                    "name": "dual",
                    "input": {"device": "stick", "type": "axis", "index": 0},
                    "transform": {
                        "type": "axis_to_dual_button",
                        "negative": {
                            "on_threshold": -0.6,
                            "off_threshold": -0.45,
                        },
                        "positive": {
                            "on_threshold": 0.6,
                            "off_threshold": 0.45,
                        },
                    },
                    "output": {
                        "type": "button",
                        "index": 21,
                        "positive_index": 22,
                    },
                }
            ],
        }
        path = _write_yaml(tmp_path, data)
        profile = load_profile(path)
        rule = profile.rules[0]
        assert rule.output.index == 21
        assert rule.output.positive_index == 22
        assert "output_button" not in rule.transform.negative
        assert "output_button" not in rule.transform.positive

    def test_transform_axis_to_dual_migrates_legacy_output_buttons(
        self, tmp_path: Path
    ) -> None:
        """旧形式の output_button 指定を出力欄のインデックスへ移行すること."""
        data = {
            "profile": {"name": "legacy_dual_test", "version": 1},
            "rules": [
                {
                    "name": "dual",
                    "input": {"device": "stick", "type": "axis", "index": 0},
                    "transform": {
                        "type": "axis_to_dual_button",
                        "negative": {
                            "output_button": 31,
                            "on_threshold": -0.6,
                            "off_threshold": -0.45,
                        },
                        "positive": {
                            "output_button": 32,
                            "on_threshold": 0.6,
                            "off_threshold": 0.45,
                        },
                    },
                    "output": {"type": "button", "index": 0},
                }
            ],
        }
        path = _write_yaml(tmp_path, data)
        profile = load_profile(path)
        rule = profile.rules[0]
        assert rule.output.index == 31
        assert rule.output.positive_index == 32

    def test_save_axis_to_dual_writes_output_indices(
        self, tmp_path: Path
    ) -> None:
        """axis_to_dual_button の出力ボタンは output にだけ保存すること."""
        profile = ProfileConfig(name="save_dual")
        profile.rules.append(
            RuleConfig(
                name="dual",
                input=InputConfig(device="stick", type="axis", index=0),
                transform=TransformConfig(
                    type="axis_to_dual_button",
                    negative={
                        "output_button": 21,
                        "on_threshold": -0.6,
                        "off_threshold": -0.45,
                    },
                    positive={
                        "output_button": 22,
                        "on_threshold": 0.6,
                        "off_threshold": 0.45,
                    },
                ),
                output=RuleOutputConfig(type="button", index=21, positive_index=22),
            )
        )
        path = tmp_path / "saved_dual.yaml"

        save_profile(profile, path)

        saved = yaml.safe_load(path.read_text(encoding="utf-8"))
        rule = saved["rules"][0]
        assert rule["output"]["index"] == 21
        assert rule["output"]["positive_index"] == 22
        assert "output_button" not in rule["transform"]["negative"]
        assert "output_button" not in rule["transform"]["positive"]


class TestProfileLoaderErrors:
    """読み込みエラーのテスト."""

    def test_nonexistent_file_raises(self) -> None:
        """存在しないファイルで ProfileLoadError が発生すること."""
        with pytest.raises(ProfileLoadError):
            load_profile("/nonexistent/path/to/profile.yaml")

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """不正なYAMLで ProfileLoadError が発生すること."""
        bad_path = tmp_path / "bad.yaml"
        bad_path.write_text("{{invalid yaml", encoding="utf-8")
        with pytest.raises(ProfileLoadError):
            load_profile(bad_path)


class TestProfileValidation:
    """バリデーションのテスト."""

    def test_empty_rule_name_loads(self, tmp_path: Path) -> None:
        """ルール名が空でもプロファイルを読み込めること."""
        data = {
            "profile": {"name": "val_test", "version": 1},
            "rules": [
                {
                    "name": "",
                    "input": {"device": "stick", "type": "axis", "index": 0},
                    "output": {"type": "axis", "name": "x"},
                }
            ],
        }
        path = _write_yaml(tmp_path, data)
        profile = load_profile(path)
        assert profile.rules[0].name == ""

    def test_empty_input_device_loads(self, tmp_path: Path) -> None:
        """input.device が空でもプロファイルを読み込めること."""
        data = {
            "profile": {"name": "val_test2", "version": 1},
            "rules": [
                {
                    "name": "test_rule",
                    "input": {"device": "", "type": "axis", "index": 0},
                    "output": {"type": "axis", "name": "x"},
                }
            ],
        }
        path = _write_yaml(tmp_path, data)
        profile = load_profile(path)
        assert profile.rules[0].input.device == ""

    def test_negative_debounce_raises(self, tmp_path: Path) -> None:
        """debounce_ms < 0 のとき ProfileValidationError が発生すること."""
        data = {
            "profile": {"name": "val_test3", "version": 1},
            "rules": [
                {
                    "name": "bad_debounce",
                    "input": {"device": "stick", "type": "button", "index": 0},
                    "filters": {"debounce_ms": -10},
                    "output": {"type": "button", "index": 1},
                }
            ],
        }
        path = _write_yaml(tmp_path, data)
        with pytest.raises(ProfileValidationError):
            load_profile(path)

    def test_negative_gap_raises(self, tmp_path: Path) -> None:
        """gap_ms < 0 のとき ProfileValidationError が発生すること."""
        data = {
            "profile": {"name": "val_test4", "version": 1},
            "rules": [
                {
                    "name": "bad_delay",
                    "input": {"device": "stick", "type": "button", "index": 0},
                    "transform": {
                        "type": "button_split",
                        "off_button": 1,
                        "gap_ms": -1,
                    },
                    "output": {"type": "button", "index": 0},
                }
            ],
        }
        path = _write_yaml(tmp_path, data)
        with pytest.raises(ProfileValidationError):
            load_profile(path)

    def test_sample_dcs_profile(self) -> None:
        """同梱のDCSプロファイルが正常に読み込めること."""
        profile_path = Path(__file__).parent.parent / "profiles" / "dcs_f16_x56.yaml"
        if not profile_path.exists():
            pytest.skip("DCS profile not found")
        profile = load_profile(profile_path)
        assert profile.name == "DCS_F16_X56"
        assert len(profile.rules) > 0

    def test_sample_msfs_profile(self) -> None:
        """同梱のMSFSプロファイルが正常に読み込めること."""
        profile_path = Path(__file__).parent.parent / "profiles" / "msfs_general.yaml"
        if not profile_path.exists():
            pytest.skip("MSFS profile not found")
        profile = load_profile(profile_path)
        assert profile.name == "MSFS_General"
        assert len(profile.rules) > 0
