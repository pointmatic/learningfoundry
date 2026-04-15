# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for the YAML curriculum parser."""

from pathlib import Path

import pytest

from learningfoundry.exceptions import (
    CurriculumValidationError,
    CurriculumVersionError,
)
from learningfoundry.parser import parse_curriculum
from learningfoundry.schema_v1 import CurriculumV1

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestValidParsing:
    def test_valid_fixture_returns_curriculum_v1(self) -> None:
        result = parse_curriculum(FIXTURES_DIR / "valid-curriculum.yml")
        assert isinstance(result, CurriculumV1)

    def test_version_is_preserved(self) -> None:
        result = parse_curriculum(FIXTURES_DIR / "valid-curriculum.yml")
        assert result.version == "1.0.0"

    def test_modules_are_parsed(self) -> None:
        result = parse_curriculum(FIXTURES_DIR / "valid-curriculum.yml")
        assert len(result.curriculum.modules) == 2

    def test_lessons_are_parsed(self) -> None:
        result = parse_curriculum(FIXTURES_DIR / "valid-curriculum.yml")
        assert len(result.curriculum.modules[0].lessons) == 1


class TestMissingVersion:
    def test_missing_version_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "curriculum.yml"
        f.write_text(
            "curriculum:\n  title: T\n  modules:\n"
            "    - id: mod-01\n      title: M\n"
            "      lessons:\n        - id: lesson-01\n          title: L\n"
            "          content_blocks: []\n"
        )
        with pytest.raises(CurriculumVersionError, match="version"):
            parse_curriculum(f)

    def test_null_version_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "curriculum.yml"
        f.write_text("version: null\ncurriculum:\n  title: T\n  modules: []\n")
        with pytest.raises(CurriculumVersionError, match="version"):
            parse_curriculum(f)


class TestUnsupportedVersion:
    def test_unsupported_major_version_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "curriculum.yml"
        f.write_text(
            "version: \"99.0.0\"\n"
            "curriculum:\n  title: T\n  modules: []\n"
        )
        with pytest.raises(CurriculumVersionError, match="99.0.0"):
            parse_curriculum(f)

    def test_error_mentions_supported_versions(self, tmp_path: Path) -> None:
        f = tmp_path / "curriculum.yml"
        f.write_text("version: \"99.0.0\"\ncurriculum:\n  title: T\n  modules: []\n")
        with pytest.raises(CurriculumVersionError, match="1.x"):
            parse_curriculum(f)

    def test_malformed_version_string_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "curriculum.yml"
        f.write_text(
            "version: \"not-a-version\"\ncurriculum:\n  title: T\n  modules: []\n"
        )
        with pytest.raises(CurriculumVersionError):
            parse_curriculum(f)


class TestMalformedYaml:
    def test_invalid_yaml_raises_validation_error(self, tmp_path: Path) -> None:
        f = tmp_path / "curriculum.yml"
        f.write_text("version: [unclosed\n")
        with pytest.raises(CurriculumValidationError, match="Malformed YAML"):
            parse_curriculum(f)

    def test_non_mapping_yaml_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "curriculum.yml"
        f.write_text("- item1\n- item2\n")
        with pytest.raises(CurriculumValidationError, match="mapping"):
            parse_curriculum(f)


class TestSchemaValidationErrors:
    def test_schema_error_raises_curriculum_validation_error(
        self, tmp_path: Path
    ) -> None:
        f = tmp_path / "curriculum.yml"
        f.write_text(
            "version: \"1.0.0\"\n"
            "curriculum:\n  title: T\n  modules: []\n"
        )
        with pytest.raises(CurriculumValidationError, match="schema validation"):
            parse_curriculum(f)


class TestFileNotFound:
    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            parse_curriculum(tmp_path / "nonexistent.yml")
