# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Edge-case and integration tests covering scenarios not exercised elsewhere."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from learningfoundry.generator import generate_app
from learningfoundry.pipeline import run_build, run_validate
from learningfoundry.resolver import (
    ResolvedContentBlock,
    ResolvedCurriculum,
    ResolvedLesson,
    ResolvedModule,
    resolve_curriculum,
)
from learningfoundry.schema_v1 import CurriculumV1

FIXTURES_DIR = Path(__file__).parent / "fixtures"
VALID_CURRICULUM = FIXTURES_DIR / "valid-curriculum.yml"
TEMPLATE_DIR = (
    Path(__file__).parent.parent
    / "src"
    / "learningfoundry"
    / "sveltekit_template"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stub_providers() -> tuple[MagicMock, MagicMock, MagicMock]:
    quiz = MagicMock()
    quiz.compile_assessment.return_value = {"quizName": "q", "questions": []}
    exercise = MagicMock()
    exercise.compile_exercise.return_value = {"status": "stub"}
    vis = MagicMock()
    vis.compile_visualization.return_value = {"status": "stub"}
    return quiz, exercise, vis


def _curriculum_with_blocks(blocks: list[dict]) -> CurriculumV1:  # type: ignore[type-arg]
    return CurriculumV1.model_validate({
        "version": "1.0.0",
        "curriculum": {
            "title": "Test",
            "modules": [
                {
                    "id": "mod-01",
                    "title": "Module One",
                    "lessons": [
                        {
                            "id": "lesson-01",
                            "title": "Lesson One",
                            "content_blocks": blocks,
                        }
                    ],
                }
            ],
        },
    })


# ---------------------------------------------------------------------------
# Empty curriculum (zero modules)
# ---------------------------------------------------------------------------


class TestEmptyCurriculum:
    def test_empty_modules_schema_error(self, tmp_path: Path) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="at least one module"):
            CurriculumV1.model_validate({
                "version": "1.0.0",
                "curriculum": {"title": "Empty", "modules": []},
            })

    def test_empty_modules_generates_valid_json(self, tmp_path: Path) -> None:
        resolved = ResolvedCurriculum(
            version="1.0.0",
            title="Empty",
            description="",
            modules=[],
        )
        out = tmp_path / "app"
        generate_app(resolved, out, template_dir=TEMPLATE_DIR)
        data = json.loads((out / "static" / "curriculum.json").read_text())
        assert data["modules"] == []

    def test_empty_modules_run_validate_returns_false(self, tmp_path: Path) -> None:
        curriculum = tmp_path / "curriculum.yml"
        curriculum.write_text(
            'version: "1.0.0"\ncurriculum:\n  title: "Empty"\n  modules: []\n'
        )
        is_valid, errors = run_validate(curriculum, base_dir=tmp_path)
        assert is_valid is False
        assert len(errors) >= 1

    def test_module_with_no_lessons_schema_error(self, tmp_path: Path) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="at least one lesson"):
            CurriculumV1.model_validate({
                "version": "1.0.0",
                "curriculum": {
                    "title": "T",
                    "modules": [
                        {"id": "mod-01", "title": "M", "lessons": []}
                    ],
                },
            })

    def test_lesson_with_no_blocks_resolves(self, tmp_path: Path) -> None:
        c = _curriculum_with_blocks([])
        result = resolve_curriculum(
            c, tmp_path,
            quiz_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert result.modules[0].lessons[0].content_blocks == []


# ---------------------------------------------------------------------------
# All block types in a single resolve
# ---------------------------------------------------------------------------


class TestAllBlockTypesTogether:
    def test_all_five_block_types_resolved_in_order(self, tmp_path: Path) -> None:
        md = tmp_path / "lesson.md"
        md.write_text("# Text block")

        quiz, exercise, vis = _stub_providers()

        c = _curriculum_with_blocks([
            {"type": "text", "ref": "lesson.md"},
            {"type": "video", "url": "https://www.youtube.com/watch?v=abc123"},
            {"type": "quiz", "source": "quizazz", "ref": "q.yml"},
            {"type": "exercise", "source": "nbfoundry", "ref": "e.yml"},
            {"type": "visualization", "source": "d3foundry", "ref": "v.yml"},
        ])
        result = resolve_curriculum(
            c, tmp_path,
            quiz_provider=quiz,
            exercise_provider=exercise,
            visualization_provider=vis,
        )
        blocks = result.modules[0].lessons[0].content_blocks
        assert len(blocks) == 5
        types = [b.type for b in blocks]
        assert types == ["text", "video", "quiz", "exercise", "visualization"]

    def test_all_block_types_are_resolved_content_blocks(self, tmp_path: Path) -> None:
        md = tmp_path / "lesson.md"
        md.write_text("Content")
        quiz, exercise, vis = _stub_providers()
        c = _curriculum_with_blocks([
            {"type": "text", "ref": "lesson.md"},
            {"type": "video", "url": "https://www.youtube.com/watch?v=abc123"},
            {"type": "quiz", "source": "quizazz", "ref": "q.yml"},
            {"type": "exercise", "source": "nbfoundry", "ref": "e.yml"},
            {"type": "visualization", "source": "d3foundry", "ref": "v.yml"},
        ])
        result = resolve_curriculum(
            c, tmp_path,
            quiz_provider=quiz,
            exercise_provider=exercise,
            visualization_provider=vis,
        )
        for block in result.modules[0].lessons[0].content_blocks:
            assert isinstance(block, ResolvedContentBlock)

    def test_curriculum_json_includes_all_block_types(self, tmp_path: Path) -> None:
        quiz, exercise, vis = _stub_providers()
        resolved = ResolvedCurriculum(
            version="1.0.0",
            title="All Blocks",
            description="",
            modules=[
                ResolvedModule(
                    id="mod-01",
                    title="M",
                    description="",
                    locked=None,
                    pre_assessment=None,
                    post_assessment=None,
                    lessons=[
                        ResolvedLesson(
                            id="lesson-01",
                            title="L",
                            content_blocks=[
                                ResolvedContentBlock(
                                    type="text", source=None, ref="l.md",
                                    content={"markdown": "Hi", "path": "/l.md"},
                                ),
                                ResolvedContentBlock(
                                    type="video", source=None, ref=None,
                                    content={"url": "https://youtu.be/abc"},
                                ),
                                ResolvedContentBlock(
                                    type="quiz", source="quizazz", ref="q.yml",
                                    content={"quizName": "q", "questions": []},
                                ),
                                ResolvedContentBlock(
                                    type="exercise", source="nbfoundry", ref="e.yml",
                                    content={"status": "stub"},
                                ),
                                ResolvedContentBlock(
                                    type="visualization", source="d3foundry",
                                    ref="v.yml", content={"status": "stub"},
                                ),
                            ],
                        )
                    ],
                )
            ],
        )
        out = tmp_path / "app"
        generate_app(resolved, out, template_dir=TEMPLATE_DIR)
        data = json.loads((out / "static" / "curriculum.json").read_text())
        blocks = data["modules"][0]["lessons"][0]["content_blocks"]
        assert len(blocks) == 5
        block_types = [b["type"] for b in blocks]
        expected = {"text", "video", "quiz", "exercise", "visualization"}
        assert set(block_types) == expected


# ---------------------------------------------------------------------------
# Large curriculum
# ---------------------------------------------------------------------------


class TestLargeCurriculum:
    N_MODULES = 5
    N_LESSONS = 4

    def _make_large_curriculum(self, tmp_path: Path) -> CurriculumV1:
        modules = []
        for m in range(self.N_MODULES):
            lessons = []
            for li in range(self.N_LESSONS):
                md = tmp_path / f"m{m}" / f"l{li}.md"
                md.parent.mkdir(parents=True, exist_ok=True)
                md.write_text(f"# Module {m} Lesson {li}")
                lessons.append({
                    "id": f"lesson-{m}-{li:02d}",
                    "title": f"Lesson {li}",
                    "content_blocks": [
                        {"type": "text", "ref": f"m{m}/l{li}.md"}
                    ],
                })
            modules.append({
                "id": f"mod-{m:02d}",
                "title": f"Module {m}",
                "lessons": lessons,
            })
        return CurriculumV1.model_validate({
            "version": "1.0.0",
            "curriculum": {"title": "Large", "modules": modules},
        })

    def test_large_curriculum_resolves_all_modules(self, tmp_path: Path) -> None:
        c = self._make_large_curriculum(tmp_path)
        result = resolve_curriculum(
            c, tmp_path,
            quiz_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert len(result.modules) == self.N_MODULES

    def test_large_curriculum_resolves_all_lessons(self, tmp_path: Path) -> None:
        c = self._make_large_curriculum(tmp_path)
        result = resolve_curriculum(
            c, tmp_path,
            quiz_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        for module in result.modules:
            assert len(module.lessons) == self.N_LESSONS

    def test_large_curriculum_generates_json_with_correct_counts(
        self, tmp_path: Path
    ) -> None:
        c = self._make_large_curriculum(tmp_path)
        result = resolve_curriculum(
            c, tmp_path,
            quiz_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        out = tmp_path / "app"
        generate_app(result, out, template_dir=TEMPLATE_DIR)
        data = json.loads((out / "static" / "curriculum.json").read_text())
        assert len(data["modules"]) == self.N_MODULES
        for mod_data in data["modules"]:
            assert len(mod_data["lessons"]) == self.N_LESSONS

    def test_large_curriculum_block_text_content_correct(
        self, tmp_path: Path
    ) -> None:
        c = self._make_large_curriculum(tmp_path)
        result = resolve_curriculum(
            c, tmp_path,
            quiz_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        # Spot-check last module, last lesson
        last_mod = result.modules[-1]
        last_lesson = last_mod.lessons[-1]
        text_block = last_lesson.content_blocks[0]
        assert "Module" in text_block.content["markdown"]


# ---------------------------------------------------------------------------
# Integration: full run_build through real generator
# ---------------------------------------------------------------------------


class TestIntegrationRunBuild:
    def test_full_build_produces_curriculum_json(self, tmp_path: Path) -> None:
        quiz, exercise, vis = _stub_providers()
        out = tmp_path / "out"
        run_build(
            VALID_CURRICULUM,
            out,
            base_dir=FIXTURES_DIR,
            quiz_provider=quiz,
            exercise_provider=exercise,
            visualization_provider=vis,
        )
        assert (out / "static" / "curriculum.json").exists()

    def test_full_build_curriculum_json_has_two_modules(
        self, tmp_path: Path
    ) -> None:
        quiz, exercise, vis = _stub_providers()
        out = tmp_path / "out"
        run_build(
            VALID_CURRICULUM,
            out,
            base_dir=FIXTURES_DIR,
            quiz_provider=quiz,
            exercise_provider=exercise,
            visualization_provider=vis,
        )
        data = json.loads((out / "static" / "curriculum.json").read_text())
        assert len(data["modules"]) == 2

    def test_full_build_curriculum_json_all_block_types_in_mod01(
        self, tmp_path: Path
    ) -> None:
        quiz, exercise, vis = _stub_providers()
        out = tmp_path / "out"
        run_build(
            VALID_CURRICULUM,
            out,
            base_dir=FIXTURES_DIR,
            quiz_provider=quiz,
            exercise_provider=exercise,
            visualization_provider=vis,
        )
        data = json.loads((out / "static" / "curriculum.json").read_text())
        mod01_blocks = data["modules"][0]["lessons"][0]["content_blocks"]
        block_types = {b["type"] for b in mod01_blocks}
        assert block_types == {"text", "video", "quiz", "exercise", "visualization"}

    def test_full_build_package_json_present(self, tmp_path: Path) -> None:
        quiz, exercise, vis = _stub_providers()
        out = tmp_path / "out"
        run_build(
            VALID_CURRICULUM,
            out,
            base_dir=FIXTURES_DIR,
            quiz_provider=quiz,
            exercise_provider=exercise,
            visualization_provider=vis,
        )
        assert (out / "package.json").exists()


# ---------------------------------------------------------------------------
# run_validate block-level content resolution error
# ---------------------------------------------------------------------------


class TestValidateResolutionErrors:
    def test_missing_text_block_file_returns_false(self, tmp_path: Path) -> None:
        curriculum = tmp_path / "curriculum.yml"
        curriculum.write_text(
            'version: "1.0.0"\n'
            "curriculum:\n  title: T\n  modules:\n"
            "    - id: mod-01\n      title: M\n      lessons:\n"
            "        - id: lesson-01\n          title: L\n"
            "          content_blocks:\n"
            "            - type: text\n              ref: nonexistent.md\n"
        )
        is_valid, errors = run_validate(curriculum, base_dir=tmp_path)
        assert is_valid is False
        assert len(errors) >= 1

    def test_resolution_error_message_includes_location(
        self, tmp_path: Path
    ) -> None:
        curriculum = tmp_path / "curriculum.yml"
        curriculum.write_text(
            'version: "1.0.0"\n'
            "curriculum:\n  title: T\n  modules:\n"
            "    - id: mod-01\n      title: M\n      lessons:\n"
            "        - id: lesson-01\n          title: L\n"
            "          content_blocks:\n"
            "            - type: text\n              ref: ghost.md\n"
        )
        is_valid, errors = run_validate(curriculum, base_dir=tmp_path)
        assert is_valid is False
        assert any("mod-01" in e or "lesson-01" in e or "ghost.md" in e
                   for e in errors)


# ---------------------------------------------------------------------------
# Optional field edge cases
# ---------------------------------------------------------------------------


class TestOptionalFields:
    def test_module_without_description_resolves(self, tmp_path: Path) -> None:
        curriculum = CurriculumV1.model_validate({
            "version": "1.0.0",
            "curriculum": {
                "title": "T",
                "modules": [
                    {
                        "id": "mod-01",
                        "title": "M",
                        "lessons": [
                            {"id": "l-01", "title": "L", "content_blocks": []}
                        ],
                    }
                ],
            },
        })
        result = resolve_curriculum(
            curriculum, tmp_path,
            quiz_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert result.modules[0].description == ""

    def test_curriculum_without_description_defaults_empty(
        self, tmp_path: Path
    ) -> None:
        curriculum = CurriculumV1.model_validate({
            "version": "1.0.0",
            "curriculum": {
                "title": "T",
                "modules": [
                    {
                        "id": "mod-01",
                        "title": "M",
                        "lessons": [
                            {"id": "l-01", "title": "L", "content_blocks": []}
                        ],
                    }
                ],
            },
        })
        result = resolve_curriculum(
            curriculum, tmp_path,
            quiz_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert result.description == ""

    def test_module_without_assessments_resolves(self, tmp_path: Path) -> None:
        curriculum = CurriculumV1.model_validate({
            "version": "1.0.0",
            "curriculum": {
                "title": "T",
                "modules": [
                    {
                        "id": "mod-01",
                        "title": "M",
                        "lessons": [
                            {"id": "l-01", "title": "L", "content_blocks": []}
                        ],
                    }
                ],
            },
        })
        result = resolve_curriculum(
            curriculum, tmp_path,
            quiz_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert result.modules[0].pre_assessment is None
        assert result.modules[0].post_assessment is None

    def test_resolved_curriculum_description_from_yaml(
        self, tmp_path: Path
    ) -> None:
        quiz, exercise, vis = _stub_providers()
        is_valid, errors = run_validate(
            VALID_CURRICULUM,
            base_dir=FIXTURES_DIR,
            quiz_provider=quiz,
            exercise_provider=exercise,
            visualization_provider=vis,
        )
        assert is_valid is True
