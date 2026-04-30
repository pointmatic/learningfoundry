# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for the curriculum YAML v1 Pydantic schema."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from learningfoundry.schema_v1 import (
    CurriculumDef,
    CurriculumV1,
    ExerciseBlock,
    Lesson,
    Module,
    QuizBlock,
    TextBlock,
    VideoBlock,
    VisualizationBlock,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:  # type: ignore[type-arg]
    with (FIXTURES_DIR / name).open() as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]


class TestValidCurriculum:
    def test_valid_fixture_parses(self) -> None:
        data = load_fixture("valid-curriculum.yml")
        curriculum = CurriculumV1.model_validate(data)
        assert curriculum.version == "1.0.0"
        assert len(curriculum.curriculum.modules) == 2

    def test_all_block_types_parsed(self) -> None:
        data = load_fixture("valid-curriculum.yml")
        curriculum = CurriculumV1.model_validate(data)
        blocks = curriculum.curriculum.modules[0].lessons[0].content_blocks
        types = [b.type for b in blocks]
        assert types == ["text", "video", "quiz", "exercise", "visualization"]

    def test_assessments_parsed(self) -> None:
        data = load_fixture("valid-curriculum.yml")
        curriculum = CurriculumV1.model_validate(data)
        mod = curriculum.curriculum.modules[0]
        assert mod.pre_assessment is not None
        assert mod.pre_assessment.source == "quizazz"
        assert mod.post_assessment is not None

    def test_optional_description_defaults_to_empty(self) -> None:
        data = load_fixture("valid-curriculum.yml")
        curriculum = CurriculumV1.model_validate(data)
        assert curriculum.curriculum.modules[1].description == ""


class TestContentBlockTypes:
    def test_text_block(self) -> None:
        block = TextBlock.model_validate({"type": "text", "ref": "content/lesson.md"})
        assert block.type == "text"
        assert block.ref == "content/lesson.md"

    def test_video_block_valid_url(self) -> None:
        block = VideoBlock.model_validate(
            {"type": "video", "url": "https://www.youtube.com/watch?v=abc123"}
        )
        assert block.type == "video"

    def test_video_block_youtu_be_url(self) -> None:
        block = VideoBlock.model_validate(
            {"type": "video", "url": "https://youtu.be/abc123"}
        )
        assert block.url == "https://youtu.be/abc123"

    def test_video_block_default_provider_and_extensions(self) -> None:
        block = VideoBlock.model_validate(
            {"type": "video", "url": "https://www.youtube.com/watch?v=abc123"}
        )
        assert block.provider == "youtube"
        assert block.extensions == {}

    def test_video_block_explicit_provider(self) -> None:
        block = VideoBlock.model_validate(
            {
                "type": "video",
                "provider": "youtube",
                "url": "https://www.youtube.com/watch?v=abc123",
            }
        )
        assert block.provider == "youtube"

    def test_video_block_extensions_dict(self) -> None:
        block = VideoBlock.model_validate(
            {
                "type": "video",
                "url": "https://youtu.be/xyz",
                "extensions": {"chapters": [{"start": 0, "title": "A"}]},
            }
        )
        assert block.extensions["chapters"][0]["title"] == "A"

    def test_quiz_block(self) -> None:
        block = QuizBlock.model_validate(
            {"type": "quiz", "source": "quizazz", "ref": "assessments/q.yml"}
        )
        assert block.source == "quizazz"

    def test_exercise_block(self) -> None:
        block = ExerciseBlock.model_validate(
            {"type": "exercise", "source": "nbfoundry", "ref": "exercises/e.yml"}
        )
        assert block.source == "nbfoundry"

    def test_visualization_block(self) -> None:
        block = VisualizationBlock.model_validate(
            {
                "type": "visualization",
                "source": "d3foundry",
                "ref": "visualizations/v.yml",
            }
        )
        assert block.source == "d3foundry"


class TestInvalidYouTubeUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "https://vimeo.com/123456",
            "https://example.com/video",
            "not-a-url",
            "http://youtube.com/",
            "https://www.youtube.com/",
        ],
    )
    def test_invalid_url_raises(self, url: str) -> None:
        with pytest.raises(ValidationError, match="YouTube"):
            VideoBlock.model_validate({"type": "video", "url": url})


class TestIdValidation:
    @pytest.mark.parametrize(
        "valid_id",
        ["mod-01", "lesson-02", "mod-abc", "lesson-01-extra", "a", "a1"],
    )
    def test_valid_ids(self, valid_id: str) -> None:
        lesson = Lesson.model_validate(
            {"id": valid_id, "title": "T", "content_blocks": []}
        )
        assert lesson.id == valid_id

    @pytest.mark.parametrize(
        "invalid_id",
        ["modOne", "mod_01", "01-mod", "MOD-01", "mod 01", "", "1"],
    )
    def test_invalid_ids_raise(self, invalid_id: str) -> None:
        with pytest.raises(ValidationError):
            Lesson.model_validate(
                {"id": invalid_id, "title": "T", "content_blocks": []}
            )


class TestDuplicateIds:
    def test_duplicate_module_ids_raise(self) -> None:
        with pytest.raises(ValidationError, match="Duplicate module id"):
            CurriculumDef.model_validate(
                {
                    "title": "T",
                    "modules": [
                        {
                            "id": "mod-01",
                            "title": "A",
                            "lessons": [
                                {"id": "lesson-01", "title": "L", "content_blocks": []}
                            ],
                        },
                        {
                            "id": "mod-01",
                            "title": "B",
                            "lessons": [
                                {"id": "lesson-02", "title": "L", "content_blocks": []}
                            ],
                        },
                    ],
                }
            )

    def test_duplicate_lesson_ids_raise(self) -> None:
        with pytest.raises(ValidationError, match="Duplicate lesson id"):
            CurriculumDef.model_validate(
                {
                    "title": "T",
                    "modules": [
                        {
                            "id": "mod-01",
                            "title": "A",
                            "lessons": [
                                {
                                    "id": "lesson-01",
                                    "title": "L",
                                    "content_blocks": [],
                                }
                            ],
                        },
                        {
                            "id": "mod-02",
                            "title": "B",
                            "lessons": [
                                {
                                    "id": "lesson-01",
                                    "title": "L",
                                    "content_blocks": [],
                                }
                            ],
                        },
                    ],
                }
            )


class TestMinimumRequirements:
    def test_zero_modules_raises(self) -> None:
        with pytest.raises(ValidationError, match="at least one module"):
            CurriculumDef.model_validate({"title": "T", "modules": []})

    def test_zero_lessons_raises(self) -> None:
        with pytest.raises(ValidationError, match="at least one lesson"):
            Module.model_validate({"id": "mod-01", "title": "T", "lessons": []})


class TestMissingRequiredFields:
    def test_missing_version_raises(self) -> None:
        with pytest.raises(ValidationError):
            CurriculumV1.model_validate(
                {
                    "curriculum": {
                        "title": "T",
                        "modules": [
                            {
                                "id": "mod-01",
                                "title": "M",
                                "lessons": [
                                    {
                                        "id": "lesson-01",
                                        "title": "L",
                                        "content_blocks": [],
                                    }
                                ],
                            }
                        ],
                    }
                }
            )

    def test_missing_title_raises(self) -> None:
        with pytest.raises(ValidationError):
            CurriculumDef.model_validate({"modules": []})

    def test_lesson_missing_title_raises(self) -> None:
        with pytest.raises(ValidationError):
            Lesson.model_validate({"id": "lesson-01", "content_blocks": []})
