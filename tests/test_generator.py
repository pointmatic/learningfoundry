# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for the SvelteKit project generator."""

import json
from pathlib import Path

import pytest

from learningfoundry.exceptions import GenerationError
from learningfoundry.generator import generate_app
from learningfoundry.resolver import (
    ResolvedCurriculum,
    ResolvedLesson,
    ResolvedModule,
)

TEMPLATE_DIR = (
    Path(__file__).parent.parent / "sveltekit_template"
)


def _make_resolved() -> ResolvedCurriculum:
    return ResolvedCurriculum(
        version="1.0.0",
        title="Test Curriculum",
        description="A test curriculum.",
        modules=[
            ResolvedModule(
                id="mod-01",
                title="Module One",
                description="",
                pre_assessment=None,
                post_assessment=None,
                lessons=[
                    ResolvedLesson(
                        id="lesson-01",
                        title="Lesson One",
                        content_blocks=[],
                    )
                ],
            )
        ],
    )


class TestOutputStructure:
    def test_output_dir_is_created(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        assert out.exists()
        assert out.is_dir()

    def test_package_json_is_present(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        assert (out / "package.json").exists()

    def test_svelte_config_is_present(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        assert (out / "svelte.config.js").exists()

    def test_curriculum_json_is_present(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        assert (out / "static" / "curriculum.json").exists()


class TestCurriculumJson:
    def test_curriculum_json_is_valid_json(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        data = json.loads((out / "static" / "curriculum.json").read_text())
        assert isinstance(data, dict)

    def test_curriculum_json_version_matches(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        resolved = _make_resolved()
        generate_app(resolved, out, template_dir=TEMPLATE_DIR)
        data = json.loads((out / "static" / "curriculum.json").read_text())
        assert data["version"] == resolved.version

    def test_curriculum_json_title_matches(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        resolved = _make_resolved()
        generate_app(resolved, out, template_dir=TEMPLATE_DIR)
        data = json.loads((out / "static" / "curriculum.json").read_text())
        assert data["title"] == resolved.title

    def test_curriculum_json_modules_present(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        resolved = _make_resolved()
        generate_app(resolved, out, template_dir=TEMPLATE_DIR)
        data = json.loads((out / "static" / "curriculum.json").read_text())
        assert len(data["modules"]) == 1
        assert data["modules"][0]["id"] == "mod-01"


class TestOverwriteBehavior:
    def test_second_call_overwrites_output(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        # Modify a file to verify it gets replaced
        sentinel = out / "static" / "curriculum.json"
        sentinel.write_text("stale content")
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        data = json.loads(sentinel.read_text())
        assert data["version"] == "1.0.0"

    def test_overwrite_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        import logging
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        with caplog.at_level(logging.WARNING, logger="learningfoundry.generator"):
            generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        assert "already exists" in caplog.text


class TestMissingTemplate:
    def test_missing_template_raises_generation_error(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        with pytest.raises(GenerationError, match="template directory not found"):
            generate_app(
                _make_resolved(),
                out,
                template_dir=tmp_path / "nonexistent_template",
            )
