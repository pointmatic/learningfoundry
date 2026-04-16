# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Shared pytest fixtures."""

import logging

import pytest


@pytest.fixture(autouse=True)
def reset_learningfoundry_logger() -> None:
    """Reset the learningfoundry root logger before each test.

    Prevents setup_logging() calls in one test from interfering with
    caplog in subsequent tests by clearing handlers and restoring propagation.
    """
    logger = logging.getLogger("learningfoundry")
    yield
    logger.handlers.clear()
    logger.propagate = True
    logger.setLevel(logging.NOTSET)
