# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""YAML curriculum parser with version dispatch."""

import logging
from pathlib import Path

import yaml
from pydantic import ValidationError

from learningfoundry.exceptions import (
    CurriculumValidationError,
    CurriculumVersionError,
)
from learningfoundry.schema_v1 import CurriculumV1

logger = logging.getLogger("learningfoundry.parser")

_SUPPORTED_MAJOR_VERSIONS = {1: CurriculumV1}


def parse_curriculum(
    yaml_path: Path,
    model_cls: type[CurriculumV1] | None = None,
) -> CurriculumV1:
    """Parse and validate a curriculum YAML file.

    1. Load raw YAML via PyYAML.
    2. Extract top-level ``version`` field.
    3. Dispatch to the correct schema/parser based on major version
       (unless ``model_cls`` is supplied — used by the schema-extensions
       pipeline to inject an extended hierarchy without losing version
       dispatch semantics for the caller).
    4. Validate via Pydantic model.
    5. Return typed, validated curriculum object.

    Args:
        yaml_path: Path to the curriculum YAML file.
        model_cls: Optional override for the Pydantic model used for
            validation. When ``None``, the major version of the YAML
            file selects the appropriate class from
            ``_SUPPORTED_MAJOR_VERSIONS``. When supplied, this class is
            used directly (must still be a ``CurriculumV1`` subclass for
            the version-string sanity check to remain meaningful).

    Returns:
        Validated ``CurriculumV1`` instance.

    Raises:
        CurriculumVersionError: Missing or unsupported version field.
        CurriculumValidationError: Schema validation failure.
        FileNotFoundError: If ``yaml_path`` does not exist.
    """
    logger.debug("Parsing curriculum: %s", yaml_path)

    try:
        raw_text = yaml_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise

    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise CurriculumValidationError(
            f"Malformed YAML in `{yaml_path}`: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise CurriculumValidationError(
            f"Curriculum YAML `{yaml_path}` must be a mapping, got "
            f"{type(data).__name__}."
        )

    version_str = data.get("version")
    if not version_str:
        raise CurriculumVersionError(
            f"Curriculum YAML `{yaml_path}` must include a top-level "
            "`version` field (semver, e.g. \"1.0.0\")."
        )

    if model_cls is None:
        model_cls = _dispatch_parser(str(version_str), yaml_path)
    else:
        # When an override is supplied we still run the version-dispatch
        # check for its error-reporting side effect — a YAML file with
        # an unsupported version should still fail loudly even if the
        # caller pre-built the model class.
        _dispatch_parser(str(version_str), yaml_path)

    try:
        curriculum = model_cls.model_validate(data)
    except ValidationError as exc:
        raise CurriculumValidationError(
            f"Curriculum `{yaml_path}` failed schema validation:\n{exc}"
        ) from exc

    logger.debug(
        "Parsed curriculum `%s` (version %s, %d modules)",
        yaml_path,
        curriculum.version,
        len(curriculum.curriculum.modules),
    )
    return curriculum


def _dispatch_parser(version_str: str, yaml_path: Path) -> type[CurriculumV1]:
    """Select the parser/schema class for the given semver string.

    Args:
        version_str: Semver string from the YAML ``version`` field.
        yaml_path: Used only for error messages.

    Returns:
        The Pydantic model class for the major version.

    Raises:
        CurriculumVersionError: If the major version is not supported.
    """
    try:
        major = int(version_str.split(".")[0])
    except (ValueError, IndexError) as exc:
        raise CurriculumVersionError(
            f"Cannot parse version `{version_str}` in `{yaml_path}`. "
            "Expected semver format (e.g. \"1.0.0\")."
        ) from exc

    model_cls = _SUPPORTED_MAJOR_VERSIONS.get(major)
    if model_cls is None:
        supported = ", ".join(f"{v}.x" for v in sorted(_SUPPORTED_MAJOR_VERSIONS))
        raise CurriculumVersionError(
            f"Unsupported curriculum version `{version_str}` in `{yaml_path}`. "
            f"Supported versions: {supported}."
        )

    return model_cls
