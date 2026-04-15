# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Logging setup for learningfoundry."""

import logging
import sys
from pathlib import Path


def setup_logging(level: str = "INFO", output: str = "stdout") -> None:
    """Configure root logger for learningfoundry.

    Args:
        level: Log level string — DEBUG, INFO, WARNING, or ERROR.
        output: Destination — "stdout" or a file path string.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    if output == "stdout":
        handler: logging.Handler = logging.StreamHandler(sys.stdout)
    else:
        handler = logging.FileHandler(Path(output))

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger("learningfoundry")
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.propagate = False
