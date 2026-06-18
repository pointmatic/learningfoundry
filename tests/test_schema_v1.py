# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for the curriculum YAML v1 Pydantic schema."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from learningfoundry.schema_v1 import (
    AfterLesson,
    AssessmentBlock,
    AssessmentDefinition,
    BeforeLesson,
    CurriculumDef,
    CurriculumMeta,
    CurriculumV1,
    ExerciseBlock,
    Hook,
    Lesson,
    LessonMeta,
    Module,
    ModuleMeta,
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
        assert types == ["text", "video", "assessment", "exercise", "visualization"]

    def test_assessments_parsed(self) -> None:
        data = load_fixture("valid-curriculum.yml")
        curriculum = CurriculumV1.model_validate(data)
        mod = curriculum.curriculum.modules[0]
        assert len(mod.assessments) == 2
        roles = [a.role for a in mod.assessments]
        assert roles == ["pre", "post"]
        assert mod.assessments[0].source == "quizazz"
        assert mod.assessments[0].position == "before_lessons"
        assert mod.assessments[1].position == "after_lessons"
        assert mod.assessments[1].pass_threshold == 0.8

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

    def test_assessment_block(self) -> None:
        block = AssessmentBlock.model_validate(
            {"type": "assessment", "source": "quizazz", "ref": "assessments/q.yml"}
        )
        assert block.source == "quizazz"

    def test_exercise_block(self) -> None:
        block = ExerciseBlock.model_validate(
            {"type": "exercise", "source": "nbfoundry", "ref": "exercises/e.yml"}
        )
        assert block.source == "nbfoundry"

    def test_exercise_block_status_defaults_to_ready(self) -> None:
        # Default `ready` so a real exercise with a typo'd ref fails loud
        # (fail-fast / OR-1) instead of silently degrading to a placeholder.
        block = ExerciseBlock.model_validate(
            {"type": "exercise", "source": "nbfoundry", "ref": "exercises/e.yml"}
        )
        assert block.status == "ready"

    def test_exercise_block_status_stub_is_explicit_opt_in(self) -> None:
        block = ExerciseBlock.model_validate(
            {
                "type": "exercise",
                "source": "nbfoundry",
                "ref": "exercises/e.yml",
                "status": "stub",
            }
        )
        assert block.status == "stub"

    def test_exercise_block_status_ready_explicit(self) -> None:
        block = ExerciseBlock.model_validate(
            {
                "type": "exercise",
                "source": "nbfoundry",
                "ref": "exercises/e.yml",
                "status": "ready",
            }
        )
        assert block.status == "ready"

    def test_exercise_block_rejects_unknown_status(self) -> None:
        with pytest.raises(ValidationError):
            ExerciseBlock.model_validate(
                {
                    "type": "exercise",
                    "source": "nbfoundry",
                    "ref": "exercises/e.yml",
                    "status": "done",
                }
            )

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


class TestLockingConfig:
    def test_locking_config_defaults(self) -> None:
        from learningfoundry.schema_v1 import LockingConfig

        lc = LockingConfig()
        assert lc.sequential is False
        assert lc.lesson_sequential is False

    def test_pass_threshold_validates_range(self) -> None:
        # Valid values
        q = AssessmentBlock.model_validate(
            {
                "type": "assessment",
                "source": "quizazz",
                "ref": "q.yml",
                "pass_threshold": 0.7,
            }
        )
        assert q.pass_threshold == 0.7

        AssessmentBlock.model_validate(
            {
                "type": "assessment",
                "source": "quizazz",
                "ref": "q.yml",
                "pass_threshold": 0.0,
            }
        )
        AssessmentBlock.model_validate(
            {
                "type": "assessment",
                "source": "quizazz",
                "ref": "q.yml",
                "pass_threshold": 1.0,
            }
        )

        # Invalid: above 1.0
        with pytest.raises(ValidationError):
            AssessmentBlock.model_validate({
                "type": "assessment", "source": "quizazz",
                "ref": "q.yml", "pass_threshold": 1.5,
            })
        # Invalid: below 0.0
        with pytest.raises(ValidationError):
            AssessmentBlock.model_validate({
                "type": "assessment", "source": "quizazz",
                "ref": "q.yml", "pass_threshold": -0.1,
            })

    def test_unlock_module_on_complete_defaults_false(self) -> None:
        lesson = Lesson.model_validate(
            {"id": "lesson-01", "title": "L", "content_blocks": []}
        )
        assert lesson.unlock_module_on_complete is False

    def test_unlock_module_on_complete_round_trips_true(self) -> None:
        lesson = Lesson.model_validate({
            "id": "lesson-01", "title": "L",
            "unlock_module_on_complete": True, "content_blocks": [],
        })
        assert lesson.unlock_module_on_complete is True

    def test_locked_absent_is_none(self) -> None:
        mod = Module.model_validate({
            "id": "mod-01", "title": "M",
            "lessons": [{"id": "lesson-01", "title": "L",
                         "content_blocks": []}],
        })
        assert mod.locked is None

    def test_locked_false(self) -> None:
        mod = Module.model_validate({
            "id": "mod-01", "title": "M", "locked": False,
            "lessons": [{"id": "lesson-01", "title": "L",
                         "content_blocks": []}],
        })
        assert mod.locked is False

    def test_locked_true(self) -> None:
        mod = Module.model_validate({
            "id": "mod-01", "title": "M", "locked": True,
            "lessons": [{"id": "lesson-01", "title": "L",
                         "content_blocks": []}],
        })
        assert mod.locked is True

    def test_full_curriculum_with_locking_round_trips(self) -> None:
        data = load_fixture("valid-curriculum.yml")
        curriculum = CurriculumV1.model_validate(data)
        assert curriculum.curriculum.locking.sequential is True
        assert curriculum.curriculum.locking.lesson_sequential is False
        assert curriculum.curriculum.modules[0].locked is False
        lesson_0 = curriculum.curriculum.modules[0].lessons[0]
        assert lesson_0.unlock_module_on_complete is True
        assessment_block = curriculum.curriculum.modules[0].lessons[0].content_blocks[2]
        assert assessment_block.pass_threshold == 0.5  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Story I.aa.2 — strict-schema rejection of misplaced fields. Pre-fix,
# Pydantic silently dropped unknown fields, so a `sequential: true` written
# at the curriculum top level (instead of nested under `locking:`) was
# eaten without a peep — the resolved curriculum.json shipped with
# `locking.sequential = false` and the entire module-locking feature was
# silently disabled.
# ---------------------------------------------------------------------------


class TestStrictSchemaRejectsExtras:
    """Misplaced or typo'd fields at curriculum / module / lesson /
    locking level should produce a clear `ValidationError`, not silent
    data loss."""

    def test_sequential_at_curriculum_level_is_rejected(self) -> None:
        # The exact mistake from the user's curriculum.yml — `sequential`
        # was written one level too high (not nested under `locking:`).
        with pytest.raises(ValidationError) as exc:
            CurriculumDef.model_validate({
                "title": "T",
                "sequential": True,
                "modules": [{
                    "id": "mod-01", "title": "M",
                    "lessons": [{"id": "lesson-01", "title": "L",
                                 "content_blocks": []}],
                }],
            })
        assert "sequential" in str(exc.value)

    def test_extra_field_at_module_level_is_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            Module.model_validate({
                "id": "mod-01", "title": "M",
                "lock": True,  # typo: should be `locked`
                "lessons": [{"id": "lesson-01", "title": "L",
                             "content_blocks": []}],
            })
        assert "lock" in str(exc.value)

    def test_extra_field_at_lesson_level_is_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            Lesson.model_validate({
                "id": "lesson-01", "title": "L",
                "optional": True,  # typo: not a real field
                "content_blocks": [],
            })
        assert "optional" in str(exc.value)

    def test_extra_field_at_locking_level_is_rejected(self) -> None:
        from learningfoundry.schema_v1 import LockingConfig
        with pytest.raises(ValidationError) as exc:
            LockingConfig.model_validate({
                "sequential": True,
                "lessson_sequential": True,  # typo: triple-s
            })
        assert "lessson_sequential" in str(exc.value)

    def test_correctly_nested_locking_still_validates(self) -> None:
        # Positive control: the *correct* shape continues to parse.
        cur = CurriculumDef.model_validate({
            "title": "T",
            "locking": {"sequential": True, "lesson_sequential": False},
            "modules": [{
                "id": "mod-01", "title": "M",
                "lessons": [{"id": "lesson-01", "title": "L",
                             "content_blocks": []}],
            }],
        })
        assert cur.locking.sequential is True
        assert cur.locking.lesson_sequential is False


class TestPedagogicalMeta:
    """Story J.a — Hook, LessonMeta, ModuleMeta and their attachment as
    optional fields on Lesson and Module."""

    def test_hook_minimal(self) -> None:
        h = Hook.model_validate({"tagline": "What if vision was a flashlight?"})
        assert h.tagline == "What if vision was a flashlight?"
        assert h.image_prompt is None

    def test_hook_with_image_prompt(self) -> None:
        h = Hook.model_validate({
            "tagline": "T",
            "image_prompt": "A 1960s neuroscience lab.",
        })
        assert h.image_prompt == "A 1960s neuroscience lab."

    def test_hook_requires_tagline(self) -> None:
        with pytest.raises(ValidationError):
            Hook.model_validate({"image_prompt": "x"})

    def test_hook_allows_extra_fields(self) -> None:
        h = Hook.model_validate({"tagline": "T", "alt_text": "x"})
        assert h.model_dump()["alt_text"] == "x"

    def test_lesson_meta_all_fields_optional(self) -> None:
        m = LessonMeta.model_validate({})
        assert m.role is None
        assert m.hook is None
        assert m.introduces == []
        assert m.reinforces == []
        assert m.duration_minutes is None

    def test_lesson_meta_full(self) -> None:
        m = LessonMeta.model_validate({
            "role": "opener",
            "hook": {"tagline": "T"},
            "introduces": ["receptive_field", "simple_cells"],
            "reinforces": [],
            "duration_minutes": 15,
        })
        assert m.role == "opener"
        assert m.hook is not None
        assert m.hook.tagline == "T"
        assert m.introduces == ["receptive_field", "simple_cells"]
        assert m.duration_minutes == 15

    def test_lesson_meta_allows_extra_fields(self) -> None:
        m = LessonMeta.model_validate({"role": "opener", "custom_field": 42})
        assert m.model_dump()["custom_field"] == 42

    def test_lesson_meta_rejects_wrong_type(self) -> None:
        with pytest.raises(ValidationError):
            LessonMeta.model_validate({"duration_minutes": "fifteen"})
        with pytest.raises(ValidationError):
            LessonMeta.model_validate({"introduces": "not-a-list"})

    def test_module_meta_all_fields_optional(self) -> None:
        m = ModuleMeta.model_validate({})
        assert m.theme is None
        assert m.big_problem is None
        assert m.objectives == []
        assert m.experiential_summary is None
        assert m.target_audience is None

    def test_module_meta_full(self) -> None:
        m = ModuleMeta.model_validate({
            "theme": "Why convolutions exist",
            "big_problem": "FC nets ignore image structure.",
            "objectives": ["Explain why FC nets fail", "Describe weight sharing"],
            "experiential_summary": "Build your first conv layer.",
            "target_audience": "Intermediate Python; high-school math",
        })
        assert m.theme == "Why convolutions exist"
        assert m.objectives == [
            "Explain why FC nets fail",
            "Describe weight sharing",
        ]

    def test_module_meta_allows_extra_fields(self) -> None:
        m = ModuleMeta.model_validate({"theme": "T", "stretch_goal": "publish"})
        assert m.model_dump()["stretch_goal"] == "publish"

    def test_lesson_meta_attaches_to_lesson(self) -> None:
        lesson = Lesson.model_validate({
            "id": "lesson-01",
            "title": "L",
            "meta": {
                "role": "opener",
                "hook": {"tagline": "T"},
                "duration_minutes": 10,
            },
            "content_blocks": [],
        })
        assert lesson.meta is not None
        assert lesson.meta.role == "opener"
        assert lesson.meta.hook is not None
        assert lesson.meta.hook.tagline == "T"

    def test_lesson_meta_absent_is_none(self) -> None:
        lesson = Lesson.model_validate({
            "id": "lesson-01", "title": "L", "content_blocks": [],
        })
        assert lesson.meta is None

    def test_module_meta_attaches_to_module(self) -> None:
        mod = Module.model_validate({
            "id": "mod-01",
            "title": "M",
            "meta": {"theme": "Why convolutions exist"},
            "lessons": [{"id": "lesson-01", "title": "L", "content_blocks": []}],
        })
        assert mod.meta is not None
        assert mod.meta.theme == "Why convolutions exist"

    def test_module_meta_absent_is_none(self) -> None:
        mod = Module.model_validate({
            "id": "mod-01", "title": "M",
            "lessons": [{"id": "lesson-01", "title": "L", "content_blocks": []}],
        })
        assert mod.meta is None

    def test_curriculum_meta_all_fields_optional(self) -> None:
        m = CurriculumMeta.model_validate({})
        assert m.target_audience is None
        assert m.objectives == []
        assert m.prerequisites == []

    def test_curriculum_meta_full(self) -> None:
        m = CurriculumMeta.model_validate({
            "target_audience": "Working software engineers new to ML",
            "objectives": ["Explain backprop", "Build a conv net"],
            "prerequisites": ["Python 3", "high-school algebra"],
        })
        assert m.target_audience == "Working software engineers new to ML"
        assert m.objectives == ["Explain backprop", "Build a conv net"]
        assert m.prerequisites == ["Python 3", "high-school algebra"]

    def test_curriculum_meta_allows_extra_fields(self) -> None:
        m = CurriculumMeta.model_validate({
            "target_audience": "x",
            "pedagogical_approach": "spiral",
        })
        assert m.model_dump()["pedagogical_approach"] == "spiral"

    def test_curriculum_meta_rejects_wrong_type(self) -> None:
        with pytest.raises(ValidationError):
            CurriculumMeta.model_validate({"objectives": "not-a-list"})
        with pytest.raises(ValidationError):
            CurriculumMeta.model_validate({"prerequisites": 42})

    def test_curriculum_meta_attaches_to_curriculum(self) -> None:
        cur = CurriculumDef.model_validate({
            "title": "T",
            "meta": {
                "target_audience": "Engineers",
                "objectives": ["Explain backprop"],
            },
            "modules": [{
                "id": "mod-01", "title": "M",
                "lessons": [{"id": "lesson-01", "title": "L",
                             "content_blocks": []}],
            }],
        })
        assert cur.meta is not None
        assert cur.meta.target_audience == "Engineers"
        assert cur.meta.objectives == ["Explain backprop"]

    def test_curriculum_meta_absent_is_none(self) -> None:
        cur = CurriculumDef.model_validate({
            "title": "T",
            "modules": [{
                "id": "mod-01", "title": "M",
                "lessons": [{"id": "lesson-01", "title": "L",
                             "content_blocks": []}],
            }],
        })
        assert cur.meta is None


class TestAssessmentDefinition:
    """Story J.e — `assessments[]` array on Module replaces the old
    two-slot `pre_assessment` / `post_assessment`. Each entry carries a
    `role` (open string), a `position` (discriminated union), `source`,
    `ref`, and an optional `pass_threshold`."""

    def _module_with_assessment(self, assessment: dict) -> dict:  # type: ignore[type-arg]
        return {
            "id": "mod-01",
            "title": "M",
            "assessments": [assessment],
            "lessons": [
                {"id": "lesson-01", "title": "L1", "content_blocks": []},
                {"id": "lesson-02", "title": "L2", "content_blocks": []},
            ],
        }

    def test_position_before_lessons_string(self) -> None:
        mod = Module.model_validate(
            self._module_with_assessment({
                "role": "pre",
                "position": "before_lessons",
                "source": "quizazz",
                "ref": "a/b.yml",
            })
        )
        assert mod.assessments[0].position == "before_lessons"

    def test_position_after_lessons_string(self) -> None:
        mod = Module.model_validate(
            self._module_with_assessment({
                "role": "post",
                "position": "after_lessons",
                "source": "quizazz",
                "ref": "a/b.yml",
            })
        )
        assert mod.assessments[0].position == "after_lessons"

    def test_position_before_lesson_mapping(self) -> None:
        mod = Module.model_validate(
            self._module_with_assessment({
                "role": "practice",
                "position": {"before_lesson": "lesson-02"},
                "source": "quizazz",
                "ref": "a/b.yml",
            })
        )
        pos = mod.assessments[0].position
        assert isinstance(pos, BeforeLesson)
        assert pos.before_lesson == "lesson-02"

    def test_position_after_lesson_mapping(self) -> None:
        mod = Module.model_validate(
            self._module_with_assessment({
                "role": "practice",
                "position": {"after_lesson": "lesson-01"},
                "source": "quizazz",
                "ref": "a/b.yml",
            })
        )
        pos = mod.assessments[0].position
        assert isinstance(pos, AfterLesson)
        assert pos.after_lesson == "lesson-01"

    def test_pass_threshold_optional(self) -> None:
        mod = Module.model_validate(
            self._module_with_assessment({
                "role": "pre",
                "position": "before_lessons",
                "source": "quizazz",
                "ref": "a/b.yml",
            })
        )
        assert mod.assessments[0].pass_threshold is None

    def test_pass_threshold_validates_range(self) -> None:
        Module.model_validate(
            self._module_with_assessment({
                "role": "post",
                "position": "after_lessons",
                "source": "quizazz",
                "ref": "a/b.yml",
                "pass_threshold": 0.7,
            })
        )
        with pytest.raises(ValidationError):
            Module.model_validate(
                self._module_with_assessment({
                    "role": "post",
                    "position": "after_lessons",
                    "source": "quizazz",
                    "ref": "a/b.yml",
                    "pass_threshold": 1.5,
                })
            )

    def test_unknown_lesson_ref_raises(self) -> None:
        with pytest.raises(ValidationError) as exc:
            Module.model_validate(
                self._module_with_assessment({
                    "role": "practice",
                    "position": {"before_lesson": "lesson-99"},
                    "source": "quizazz",
                    "ref": "a/b.yml",
                })
            )
        msg = str(exc.value)
        assert "lesson-99" in msg
        assert "mod-01" in msg
        assert "practice" in msg

    def test_invalid_position_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Module.model_validate(
                self._module_with_assessment({
                    "role": "pre",
                    "position": "anywhere",  # not a Literal value
                    "source": "quizazz",
                    "ref": "a/b.yml",
                })
            )

    def test_assessments_default_empty(self) -> None:
        mod = Module.model_validate({
            "id": "mod-01", "title": "M",
            "lessons": [{"id": "lesson-01", "title": "L", "content_blocks": []}],
        })
        assert mod.assessments == []

    def test_extra_field_on_assessment_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AssessmentDefinition.model_validate({
                "role": "pre",
                "position": "before_lessons",
                "source": "quizazz",
                "ref": "a/b.yml",
                "stranger": "danger",  # not a real field
            })

    def test_module_with_pre_assessment_field_rejected(self) -> None:
        # Removed in Story J.e — strict-mode rejects the legacy field.
        with pytest.raises(ValidationError) as exc:
            Module.model_validate({
                "id": "mod-01", "title": "M",
                "pre_assessment": {"source": "quizazz", "ref": "x.yml"},
                "lessons": [
                    {"id": "lesson-01", "title": "L", "content_blocks": []}
                ],
            })
        assert "pre_assessment" in str(exc.value)


class TestAssessmentIdAutoGen:
    """Story J.r — optional `id` field on `AssessmentDefinition` plus
    role-based auto-gen and intra-module uniqueness validation."""

    def _module(self, assessments: list[dict]) -> dict:  # type: ignore[type-arg]
        return {
            "id": "mod-01",
            "title": "M",
            "assessments": assessments,
            "lessons": [
                {"id": "lesson-01", "title": "L1", "content_blocks": []},
                {"id": "lesson-02", "title": "L2", "content_blocks": []},
            ],
        }

    def test_autogen_all_omitted(self) -> None:
        mod = Module.model_validate(self._module([
            {"role": "pre", "position": "before_lessons",
             "source": "quizazz", "ref": "p.yml"},
            {"role": "post", "position": "after_lessons",
             "source": "quizazz", "ref": "po.yml"},
            {"role": "practice", "position": {"before_lesson": "lesson-01"},
             "source": "quizazz", "ref": "pr1.yml"},
            {"role": "practice", "position": {"before_lesson": "lesson-02"},
             "source": "quizazz", "ref": "pr2.yml"},
        ]))
        assert [a.id for a in mod.assessments] == [
            "pre", "post", "practice", "practice-2",
        ]

    def test_autogen_mixed_with_explicit(self) -> None:
        mod = Module.model_validate(self._module([
            {"id": "diagnostic",
             "role": "pre", "position": "before_lessons",
             "source": "quizazz", "ref": "p.yml"},
            {"role": "practice", "position": {"before_lesson": "lesson-01"},
             "source": "quizazz", "ref": "pr1.yml"},
            {"id": "final",
             "role": "post", "position": "after_lessons",
             "source": "quizazz", "ref": "po.yml"},
            {"role": "practice", "position": {"before_lesson": "lesson-02"},
             "source": "quizazz", "ref": "pr2.yml"},
        ]))
        assert [a.id for a in mod.assessments] == [
            "diagnostic", "practice", "final", "practice-2",
        ]

    def test_duplicate_explicit_ids_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            Module.model_validate(self._module([
                {"id": "pre", "role": "pre", "position": "before_lessons",
                 "source": "quizazz", "ref": "a.yml"},
                {"id": "pre", "role": "pre",
                 "position": {"before_lesson": "lesson-01"},
                 "source": "quizazz", "ref": "b.yml"},
            ]))
        msg = str(exc.value)
        assert "mod-01" in msg
        assert "pre" in msg

    def test_explicit_collides_with_autogen_rejected(self) -> None:
        # Three `practice` roles; explicit `practice-2` collides with
        # the auto-gen result for the second practice in author order.
        with pytest.raises(ValidationError) as exc:
            Module.model_validate(self._module([
                {"role": "practice",
                 "position": {"before_lesson": "lesson-01"},
                 "source": "quizazz", "ref": "a.yml"},
                {"role": "practice",
                 "position": {"before_lesson": "lesson-02"},
                 "source": "quizazz", "ref": "b.yml"},
                {"id": "practice-2", "role": "practice",
                 "position": {"after_lesson": "lesson-02"},
                 "source": "quizazz", "ref": "c.yml"},
            ]))
        msg = str(exc.value)
        assert "mod-01" in msg
        assert "practice-2" in msg
