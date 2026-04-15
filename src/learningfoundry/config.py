# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Global configuration loading and precedence merging for learningfoundry."""

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from learningfoundry.exceptions import ConfigError

logger = logging.getLogger("learningfoundry.config")

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "learningfoundry" / "config.yml"

_KNOWN_KEYS: dict[str, set[str]] = {
    "logging": {"level", "output"},
}


@dataclass
class LoggingConfig:
    level: str = "INFO"
    output: str = "stdout"


@dataclass
class AppConfig:
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def load_config(
    config_path: Path | None = None,
    cli_overrides: dict[str, str] | None = None,
) -> AppConfig:
    """Load configuration with precedence: CLI flags > config file > built-in defaults.

    Args:
        config_path: Explicit path to config file. Falls back to
            ``~/.config/learningfoundry/config.yml`` if None.
        cli_overrides: Dict of CLI flag overrides, e.g.
            ``{"log_level": "DEBUG", "log_output": "stdout"}``.

    Returns:
        Merged ``AppConfig`` instance.

    Raises:
        ConfigError: If the config file contains malformed YAML.
    """
    config = AppConfig()

    resolved_path = config_path or DEFAULT_CONFIG_PATH
    if resolved_path.exists():
        try:
            raw = yaml.safe_load(resolved_path.read_text())
        except yaml.YAMLError as exc:
            raise ConfigError(
                f"Invalid config file at `{resolved_path}`: {exc}"
            ) from exc

        if raw is not None:
            _warn_unknown_keys(raw, resolved_path)
            logging_raw = raw.get("logging", {})
            if "level" in logging_raw:
                config.logging.level = logging_raw["level"]
            if "output" in logging_raw:
                config.logging.output = logging_raw["output"]

    if cli_overrides:
        if "log_level" in cli_overrides and cli_overrides["log_level"] is not None:
            config.logging.level = cli_overrides["log_level"]
        if "log_output" in cli_overrides and cli_overrides["log_output"] is not None:
            config.logging.output = cli_overrides["log_output"]

    return config


def _warn_unknown_keys(raw: dict[str, object], config_path: Path) -> None:
    for top_key, value in raw.items():
        if top_key not in _KNOWN_KEYS:
            logger.warning(
                "Unknown config key `%s` in `%s` — ignoring.", top_key, config_path
            )
            continue
        if isinstance(value, dict):
            known_sub = _KNOWN_KEYS[top_key]
            for sub_key in value:
                if sub_key not in known_sub:
                    logger.warning(
                        "Unknown config key `%s.%s` in `%s` — ignoring.",
                        top_key,
                        sub_key,
                        config_path,
                    )
