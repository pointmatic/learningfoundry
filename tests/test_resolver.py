# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for the content resolver."""

import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from learningfoundry.exceptions import ContentResolutionError
from learningfoundry.resolver import (
    ResolvedContentBlock,
    ResolvedCurriculum,
    ResolvedLesson,
    ResolvedModule,
    resolve_curriculum,
)
from learningfoundry.schema_v1 import CurriculumV1

_VALID_CURRICULUM = {
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
                        "content_blocks": [],
                    }
                ],
            }
        ],
    },
}


def _make_curriculum(**overrides: object) -> CurriculumV1:
    data = dict(_VALID_CURRICULUM)
    data.update(overrides)
    return CurriculumV1.model_validate(data)


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


class TestResolvedTypes:
    def test_returns_resolved_curriculum(self, tmp_path: Path) -> None:
        c = _make_curriculum()
        result = resolve_curriculum(
            c, tmp_path,
            quiz_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert isinstance(result, ResolvedCurriculum)

    def test_resolved_curriculum_has_modules(self, tmp_path: Path) -> None:
        c = _make_curriculum()
        result = resolve_curriculum(
            c, tmp_path,
            quiz_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert len(result.modules) == 1
        assert isinstance(result.modules[0], ResolvedModule)

    def test_resolved_module_has_lessons(self, tmp_path: Path) -> None:
        c = _make_curriculum()
        result = resolve_curriculum(
            c, tmp_path,
            quiz_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert len(result.modules[0].lessons) == 1
        assert isinstance(result.modules[0].lessons[0], ResolvedLesson)

    def test_metadata_preserved(self, tmp_path: Path) -> None:
        c = _make_curriculum()
        result = resolve_curriculum(
            c, tmp_path,
            quiz_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert result.version == "1.0.0"
        assert result.title == "Test"


class TestTextBlockResolution:
    def test_text_block_reads_markdown(self, tmp_path: Path) -> None:
        md = tmp_path / "content" / "lesson.md"
        md.parent.mkdir()
        md.write_text("# Hello\nSome content.")
        c = _curriculum_with_blocks([{"type": "text", "ref": "content/lesson.md"}])
        result = resolve_curriculum(
            c, tmp_path,
            quiz_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        block = result.modules[0].lessons[0].content_blocks[0]
        assert isinstance(block, ResolvedContentBlock)
        assert block.type == "text"
        assert "# Hello" in block.content["markdown"]

    def test_missing_markdown_raises_content_resolution_error(
        self, tmp_path: Path
    ) -> None:
        c = _curriculum_with_blocks(
            [{"type": "text", "ref": "content/missing.md"}]
        )
        with pytest.raises(ContentResolutionError, match="not found"):
            resolve_curriculum(
                c, tmp_path,
                quiz_provider=MagicMock(),
                exercise_provider=MagicMock(),
                visualization_provider=MagicMock(),
            )

    def test_error_includes_block_location(self, tmp_path: Path) -> None:
        c = _curriculum_with_blocks(
            [{"type": "text", "ref": "content/missing.md"}]
        )
        with pytest.raises(ContentResolutionError, match="mod-01"):
            resolve_curriculum(
                c, tmp_path,
                quiz_provider=MagicMock(),
                exercise_provider=MagicMock(),
                visualization_provider=MagicMock(),
            )

    def test_empty_markdown_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        md = tmp_path / "empty.md"
        md.write_text("")
        c = _curriculum_with_blocks([{"type": "text", "ref": "empty.md"}])
        with caplog.at_level(logging.WARNING, logger="learningfoundry.resolver"):
            resolve_curriculum(
                c, tmp_path,
                quiz_provider=MagicMock(),
                exercise_provider=MagicMock(),
                visualization_provider=MagicMock(),
            )
        assert "empty" in caplog.text.lower()


class TestVideoBlockResolution:
    def test_valid_youtube_url_resolved(self, tmp_path: Path) -> None:
        c = _curriculum_with_blocks(
            [{"type": "video", "url": "https://www.youtube.com/watch?v=abc123"}]
        )
        result = resolve_curriculum(
            c, tmp_path,
            quiz_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        block = result.modules[0].lessons[0].content_blocks[0]
        assert block.type == "video"
        assert block.content["url"] == "https://www.youtube.com/watch?v=abc123"

    def test_invalid_url_raises_content_resolution_error(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(ValueError):
            _curriculum_with_blocks(
                [{"type": "video", "url": "https://vimeo.com/12345"}]
            )


class TestQuizBlockResolution:
    def test_delegates_to_quiz_provider(self, tmp_path: Path) -> None:
        mock_quiz = MagicMock()
        mock_quiz.compile_assessment.return_value = {"quizName": "q1", "questions": []}
        c = _curriculum_with_blocks(
            [{"type": "quiz", "source": "quizazz", "ref": "assessments/q.yml"}]
        )
        result = resolve_curriculum(
            c, tmp_path,
            quiz_provider=mock_quiz,
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        mock_quiz.compile_assessment.assert_called_once_with(
            Path("assessments/q.yml"), tmp_path
        )
        block = result.modules[0].lessons[0].content_blocks[0]
        assert block.type == "quiz"
        assert block.content["quizName"] == "q1"

    def test_provider_error_wrapped_with_location(self, tmp_path: Path) -> None:
        mock_quiz = MagicMock()
        mock_quiz.compile_assessment.side_effect = RuntimeError("bad quiz")
        c = _curriculum_with_blocks(
            [{"type": "quiz", "source": "quizazz", "ref": "assessments/q.yml"}]
        )
        with pytest.raises(ContentResolutionError, match="lesson-01"):
            resolve_curriculum(
                c, tmp_path,
                quiz_provider=mock_quiz,
                exercise_provider=MagicMock(),
                visualization_provider=MagicMock(),
            )


class TestExerciseBlockResolution:
    def test_delegates_to_exercise_provider(self, tmp_path: Path) -> None:
        mock_ex = MagicMock()
        mock_ex.compile_exercise.return_value = {"status": "stub", "title": "Ex"}
        c = _curriculum_with_blocks(
            [{"type": "exercise", "source": "nbfoundry", "ref": "exercises/e.yml"}]
        )
        result = resolve_curriculum(
            c, tmp_path,
            quiz_provider=MagicMock(),
            exercise_provider=mock_ex,
            visualization_provider=MagicMock(),
        )
        mock_ex.compile_exercise.assert_called_once_with(
            Path("exercises/e.yml"), tmp_path
        )
        block = result.modules[0].lessons[0].content_blocks[0]
        assert block.type == "exercise"


class TestVisualizationBlockResolution:
    def test_delegates_to_visualization_provider(self, tmp_path: Path) -> None:
        mock_vis = MagicMock()
        mock_vis.compile_visualization.return_value = {
            "status": "stub", "title": "Vis"
        }
        c = _curriculum_with_blocks(
            [
                {
                    "type": "visualization",
                    "source": "d3foundry",
                    "ref": "visualizations/v.yml",
                }
            ]
        )
        result = resolve_curriculum(
            c, tmp_path,
            quiz_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=mock_vis,
        )
        mock_vis.compile_visualization.assert_called_once_with(
            Path("visualizations/v.yml"), tmp_path
        )
        block = result.modules[0].lessons[0].content_blocks[0]
        assert block.type == "visualization"


class TestAssessmentResolution:
    def test_pre_assessment_resolved(self, tmp_path: Path) -> None:
        mock_quiz = MagicMock()
        mock_quiz.compile_assessment.return_value = {"quizName": "pre"}
        curriculum = CurriculumV1.model_validate({
            "version": "1.0.0",
            "curriculum": {
                "title": "T",
                "modules": [
                    {
                        "id": "mod-01",
                        "title": "M",
                        "pre_assessment": {
                            "source": "quizazz",
                            "ref": "assessments/pre.yml",
                        },
                        "lessons": [
                            {
                                "id": "lesson-01",
                                "title": "L",
                                "content_blocks": [],
                            }
                        ],
                    }
                ],
            },
        })
        result = resolve_curriculum(
            curriculum, tmp_path,
            quiz_provider=mock_quiz,
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert result.modules[0].pre_assessment == {"quizName": "pre"}

    def test_assessment_error_raises_content_resolution_error(
        self, tmp_path: Path
    ) -> None:
        mock_quiz = MagicMock()
        mock_quiz.compile_assessment.side_effect = RuntimeError("broken")
        curriculum = CurriculumV1.model_validate({
            "version": "1.0.0",
            "curriculum": {
                "title": "T",
                "modules": [
                    {
                        "id": "mod-01",
                        "title": "M",
                        "pre_assessment": {
                            "source": "quizazz",
                            "ref": "assessments/pre.yml",
                        },
                        "lessons": [
                            {
                                "id": "lesson-01",
                                "title": "L",
                                "content_blocks": [],
                            }
                        ],
                    }
                ],
            },
        })
        with pytest.raises(ContentResolutionError, match="pre_assessment"):
            resolve_curriculum(
                curriculum, tmp_path,
                quiz_provider=mock_quiz,
                exercise_provider=MagicMock(),
                visualization_provider=MagicMock(),
            )
