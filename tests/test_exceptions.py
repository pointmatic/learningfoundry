# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for the learningfoundry exception hierarchy."""

import logging

import pytest

from learningfoundry.exceptions import (
    ConfigError,
    ContentResolutionError,
    CurriculumValidationError,
    CurriculumVersionError,
    GenerationError,
    IntegrationError,
    LearningFoundryError,
)
from learningfoundry.logging_config import setup_logging


class TestExceptionHierarchy:
    def test_base_is_exception(self) -> None:
        assert issubclass(LearningFoundryError, Exception)

    def test_config_error_inherits_base(self) -> None:
        assert issubclass(ConfigError, LearningFoundryError)

    def test_curriculum_version_error_inherits_base(self) -> None:
        assert issubclass(CurriculumVersionError, LearningFoundryError)

    def test_curriculum_validation_error_inherits_base(self) -> None:
        assert issubclass(CurriculumValidationError, LearningFoundryError)

    def test_content_resolution_error_inherits_base(self) -> None:
        assert issubclass(ContentResolutionError, LearningFoundryError)

    def test_integration_error_inherits_base(self) -> None:
        assert issubclass(IntegrationError, LearningFoundryError)

    def test_generation_error_inherits_base(self) -> None:
        assert issubclass(GenerationError, LearningFoundryError)

    def test_all_catchable_as_base(self) -> None:
        subclasses = [
            ConfigError,
            CurriculumVersionError,
            CurriculumValidationError,
            ContentResolutionError,
            IntegrationError,
            GenerationError,
        ]
        for cls in subclasses:
            with pytest.raises(LearningFoundryError):
                raise cls("test message")

    def test_string_representation(self) -> None:
        err = CurriculumVersionError("Unsupported version: 99.0.0")
        assert "Unsupported version: 99.0.0" in str(err)

    def test_integration_error_wraps_cause(self) -> None:
        cause = ValueError("quizazz parse failed")
        err = IntegrationError("mod-01/lesson-01/block[0]: quizazz parse failed")
        err.__cause__ = cause
        assert "mod-01" in str(err)


class TestLoggingSetup:
    def teardown_method(self) -> None:
        logger = logging.getLogger("learningfoundry")
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(logging.NOTSET)

    def test_default_level_is_info(self) -> None:
        setup_logging()
        logger = logging.getLogger("learningfoundry")
        assert logger.level == logging.INFO

    def test_debug_level(self) -> None:
        setup_logging(level="DEBUG")
        logger = logging.getLogger("learningfoundry")
        assert logger.level == logging.DEBUG

    def test_warning_level(self) -> None:
        setup_logging(level="WARNING")
        logger = logging.getLogger("learningfoundry")
        assert logger.level == logging.WARNING

    def test_stdout_handler(self) -> None:
        setup_logging(output="stdout")
        logger = logging.getLogger("learningfoundry")
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)

    def test_file_handler(self, tmp_path: pytest.TempPathFactory) -> None:
        log_file = str(tmp_path / "test.log")  # type: ignore[operator]
        setup_logging(output=log_file)
        logger = logging.getLogger("learningfoundry")
        assert isinstance(logger.handlers[0], logging.FileHandler)
        logger.info("test entry")
        with open(log_file) as f:
            assert "test entry" in f.read()

    def test_no_propagation(self) -> None:
        setup_logging()
        logger = logging.getLogger("learningfoundry")
        assert logger.propagate is False

    def test_repeated_setup_does_not_duplicate_handlers(self) -> None:
        setup_logging()
        setup_logging()
        logger = logging.getLogger("learningfoundry")
        assert len(logger.handlers) == 1
