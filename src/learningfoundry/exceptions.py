# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Exception hierarchy for learningfoundry."""


class LearningFoundryError(Exception):
    """Base exception for all learningfoundry errors."""


class ConfigError(LearningFoundryError):
    """Config file is malformed or contains invalid values."""


class CurriculumVersionError(LearningFoundryError):
    """Missing or unsupported curriculum YAML version."""


class CurriculumValidationError(LearningFoundryError):
    """Curriculum YAML fails schema validation.

    Includes field path and validation detail from Pydantic.
    """


class ContentResolutionError(LearningFoundryError):
    """Content reference cannot be resolved.

    Includes block location (module/lesson/block index) and specific cause.
    """


class IntegrationError(LearningFoundryError):
    """An integration library (quizazz, nbfoundry, d3foundry) returned an error.

    Wraps the library's original error with block location context.
    """


class GenerationError(LearningFoundryError):
    """SvelteKit project generation failed."""
