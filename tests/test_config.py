# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for global configuration loading and precedence merging."""

import logging
from pathlib import Path

import pytest

from learningfoundry.config import AppConfig, LoggingConfig, load_config
from learningfoundry.exceptions import ConfigError


class TestDefaults:
    def test_default_log_level_is_info(self, tmp_path: Path) -> None:
        config = load_config(config_path=tmp_path / "nonexistent.yml")
        assert config.logging.level == "INFO"

    def test_default_log_output_is_stdout(self, tmp_path: Path) -> None:
        config = load_config(config_path=tmp_path / "nonexistent.yml")
        assert config.logging.output == "stdout"

    def test_returns_app_config_instance(self, tmp_path: Path) -> None:
        config = load_config(config_path=tmp_path / "nonexistent.yml")
        assert isinstance(config, AppConfig)
        assert isinstance(config.logging, LoggingConfig)


class TestConfigFileOverrides:
    def test_log_level_from_file(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yml"
        cfg.write_text("logging:\n  level: DEBUG\n")
        config = load_config(config_path=cfg)
        assert config.logging.level == "DEBUG"

    def test_log_output_from_file(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yml"
        cfg.write_text("logging:\n  output: /var/log/lf.log\n")
        config = load_config(config_path=cfg)
        assert config.logging.output == "/var/log/lf.log"

    def test_partial_override_preserves_defaults(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yml"
        cfg.write_text("logging:\n  level: WARNING\n")
        config = load_config(config_path=cfg)
        assert config.logging.level == "WARNING"
        assert config.logging.output == "stdout"

    def test_empty_config_file_uses_defaults(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yml"
        cfg.write_text("")
        config = load_config(config_path=cfg)
        assert config.logging.level == "INFO"
        assert config.logging.output == "stdout"


class TestCliOverrides:
    def test_cli_overrides_default(self, tmp_path: Path) -> None:
        config = load_config(
            config_path=tmp_path / "nonexistent.yml",
            cli_overrides={"log_level": "ERROR"},
        )
        assert config.logging.level == "ERROR"

    def test_cli_overrides_config_file(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yml"
        cfg.write_text("logging:\n  level: DEBUG\n")
        config = load_config(
            config_path=cfg,
            cli_overrides={"log_level": "WARNING"},
        )
        assert config.logging.level == "WARNING"

    def test_cli_none_value_does_not_override(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yml"
        cfg.write_text("logging:\n  level: DEBUG\n")
        config = load_config(
            config_path=cfg,
            cli_overrides={"log_level": None},  # type: ignore[dict-item]
        )
        assert config.logging.level == "DEBUG"

    def test_cli_output_override(self, tmp_path: Path) -> None:
        log_file = str(tmp_path / "out.log")
        config = load_config(
            config_path=tmp_path / "nonexistent.yml",
            cli_overrides={"log_output": log_file},
        )
        assert config.logging.output == log_file


class TestMalformedConfig:
    def test_malformed_yaml_raises_config_error(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yml"
        cfg.write_text("logging:\n  level: [unclosed\n")
        with pytest.raises(ConfigError, match="Invalid config file"):
            load_config(config_path=cfg)

    def test_config_error_includes_path(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yml"
        cfg.write_text("logging:\n  level: [unclosed\n")
        with pytest.raises(ConfigError) as exc_info:
            load_config(config_path=cfg)
        assert str(cfg) in str(exc_info.value)


class TestUnknownKeys:
    def test_unknown_top_level_key_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        cfg = tmp_path / "config.yml"
        cfg.write_text("logging:\n  level: INFO\nunknown_key: value\n")
        with caplog.at_level(logging.WARNING, logger="learningfoundry.config"):
            load_config(config_path=cfg)
        assert "unknown_key" in caplog.text

    def test_unknown_sub_key_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        cfg = tmp_path / "config.yml"
        cfg.write_text("logging:\n  level: INFO\n  mystery: true\n")
        with caplog.at_level(logging.WARNING, logger="learningfoundry.config"):
            load_config(config_path=cfg)
        assert "mystery" in caplog.text

    def test_unknown_keys_do_not_raise(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yml"
        cfg.write_text("logging:\n  level: INFO\nunknown_key: value\n")
        config = load_config(config_path=cfg)
        assert config.logging.level == "INFO"
