# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Pydantic models for curriculum YAML v1 schema."""

import re
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    """Base for every curriculum-schema model.

    `extra='forbid'` makes Pydantic raise `ValidationError` on unknown
    fields instead of silently dropping them — Story I.aa.2 root cause
    was a `sequential: true` mis-placed at the curriculum top level
    instead of nested under `locking:`. The unknown field was discarded
    without a peep, the resolved curriculum.json shipped with
    `locking.sequential = false`, and the entire module-locking feature
    was silently disabled. Strict validation converts that class of typo
    into a loud build-time error pointing at the offending field name.
    """

    model_config = ConfigDict(extra="forbid")

_ID_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
YOUTUBE_URL_RE = re.compile(
    r"^https?://(www\.)?(youtube\.com/watch\?.*v=|youtu\.be/)[\w\-]+"
)

# Supported ``video`` block players. Extend with new literals (e.g. ``"vimeo"``)
# when a resolver + frontend implementation exists.
VideoProvider = Literal["youtube"]


def _validate_id(v: str, field_name: str = "id") -> str:
    if not _ID_RE.match(v):
        raise ValueError(
            f"Invalid {field_name} `{v}`: must be lowercase, hyphenated "
            "(e.g. `mod-01`, `lesson-02`)."
        )
    return v


class BeforeLesson(StrictModel):
    """Assessment positioned immediately before the named lesson (Story J.e)."""

    before_lesson: str


class AfterLesson(StrictModel):
    """Assessment positioned immediately after the named lesson (Story J.e)."""

    after_lesson: str


# `position` discriminated union for `AssessmentDefinition`. The two
# string literals anchor to the start / end of the lesson list; the two
# model variants anchor to a specific lesson by id (validated against
# `Module.lessons` via a `model_validator` on `Module`).
AssessmentPosition = (
    Literal["before_lessons", "after_lessons"] | BeforeLesson | AfterLesson
)


class AssessmentDefinition(StrictModel):
    """A single assessment (quiz, exam, ...) bound to a module at a
    declared position. Replaces the previous two-slot
    ``pre_assessment`` / ``post_assessment`` fields (Story J.e).

    ``role`` is an open string — conventional values are ``pre``,
    ``practice``, ``post``, ``checkpoint`` — used as a UI label and a
    tag for downstream consumers; the schema does not constrain the
    vocabulary.

    ``id`` is an optional stable identifier used by the route layer
    (Story J.s) and the progress store (Story J.u). If omitted, an id
    is auto-generated from ``role``: the first assessment with a given
    role takes the bare role as id (``pre``, ``post``, ``practice``),
    and subsequent assessments with the same role append a 1-based
    counter (``practice-2``, ``practice-3``). Authors override by
    supplying an explicit ``id:`` in YAML. After auto-gen,
    ``Module`` validates intra-module uniqueness of the final id set,
    so duplicate explicit ids fail loud at parse time (Story J.r).
    """

    id: str | None = None
    role: str
    position: AssessmentPosition
    source: str
    ref: str
    pass_threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class TextBlock(StrictModel):
    type: Literal["text"]
    ref: str


class VideoBlock(StrictModel):
    """Video embed. ``provider`` selects the player; ``extensions`` carries
    player-specific options (chapters, transcript refs, etc.) without
    forcing a one-size-fits-all schema across providers.
    """

    type: Literal["video"]
    url: str
    provider: VideoProvider = "youtube"
    extensions: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_url_for_provider(self) -> Self:
        if self.provider == "youtube":
            if not YOUTUBE_URL_RE.match(self.url):
                raise ValueError(
                    f"Invalid YouTube URL `{self.url}`. "
                    "Expected format: https://www.youtube.com/watch?v=... "
                    "or https://youtu.be/..."
                )
        return self


class AssessmentBlock(StrictModel):
    type: Literal["assessment"]
    source: str
    ref: str
    pass_threshold: float = Field(0.0, ge=0.0, le=1.0)


class ExerciseBlock(StrictModel):
    type: Literal["exercise"]
    source: str
    ref: str


class VisualizationBlock(StrictModel):
    type: Literal["visualization"]
    source: str
    ref: str


ContentBlock = Annotated[
    TextBlock | VideoBlock | AssessmentBlock | ExerciseBlock | VisualizationBlock,
    ...,
]


class Hook(StrictModel):
    """Opening hook for a lesson — a tagline and optional image prompt.

    ``extra='allow'`` lets authors attach genre-specific fields without
    schema churn (Phase J pedagogical-authoring contract).
    """

    model_config = ConfigDict(extra="allow")

    tagline: str
    image_prompt: str | None = None


class LessonMeta(StrictModel):
    """Pedagogical metadata for a lesson.

    All fields are optional; the meta block as a whole is optional on
    ``Lesson``. ``extra='allow'`` so authors can attach their own fields.
    """

    model_config = ConfigDict(extra="allow")

    role: str | None = None
    hook: Hook | None = None
    introduces: list[str] = Field(default_factory=list)
    reinforces: list[str] = Field(default_factory=list)
    duration_minutes: int | None = None


class ModuleMeta(StrictModel):
    """Pedagogical metadata for a module.

    All fields are optional; the meta block as a whole is optional on
    ``Module``. ``extra='allow'`` so authors can attach their own fields.
    """

    model_config = ConfigDict(extra="allow")

    theme: str | None = None
    big_problem: str | None = None
    objectives: list[str] = Field(default_factory=list)
    experiential_summary: str | None = None
    target_audience: str | None = None


class CurriculumMeta(StrictModel):
    """Pedagogical metadata for a curriculum as a whole (Story J.h).

    All fields are optional; the meta block as a whole is optional on
    ``CurriculumDef``. ``extra='allow'`` so authors can attach their own
    fields, and the schema-extensions mechanism (Story J.h) can tighten
    that escape hatch into strict whitelist validation per project.
    """

    model_config = ConfigDict(extra="allow")

    target_audience: str | None = None
    objectives: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)


class Lesson(StrictModel):
    id: str
    title: str
    unlock_module_on_complete: bool = False
    meta: LessonMeta | None = None
    content_blocks: list[ContentBlock]

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        return _validate_id(v, "lesson id")


class Module(StrictModel):
    id: str
    title: str
    description: str = ""
    locked: bool | None = None
    meta: ModuleMeta | None = None
    assessments: list[AssessmentDefinition] = Field(default_factory=list)
    lessons: list[Lesson]

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        return _validate_id(v, "module id")

    @model_validator(mode="after")
    def check_has_lessons(self) -> "Module":
        if not self.lessons:
            raise ValueError(f"Module `{self.id}` must contain at least one lesson.")
        return self

    @model_validator(mode="after")
    def autogen_assessment_ids(self) -> "Module":
        """Fill in ``id`` for assessments that omit it, then assert
        intra-module uniqueness of the final id set (Story J.r).

        Auto-gen uses the assessment's role-order within the module:
        the Nth assessment carrying role ``R`` (N is 1-based) gets id
        ``R`` if N == 1, else ``R-{N}``. Explicit ids are honoured
        verbatim — auto-gen does **not** skip over them when counting,
        so an explicit id chosen to look like an auto-gen value will
        collide and fail uniqueness validation here.
        """
        role_counts: dict[str, int] = {}
        for assessment in self.assessments:
            role_counts[assessment.role] = role_counts.get(assessment.role, 0) + 1
            if assessment.id is None:
                n = role_counts[assessment.role]
                assessment.id = (
                    assessment.role if n == 1 else f"{assessment.role}-{n}"
                )

        seen: set[str] = set()
        for assessment in self.assessments:
            assert assessment.id is not None  # auto-gen guarantees this
            if assessment.id in seen:
                raise ValueError(
                    f"Module `{self.id}` has duplicate assessment id "
                    f"`{assessment.id}`. Assessment ids must be unique "
                    "within a module; check explicit `id:` values and "
                    "any collisions with role-based auto-gen "
                    "(`pre`, `practice-2`, ...)."
                )
            seen.add(assessment.id)
        return self

    @model_validator(mode="after")
    def validate_assessment_lesson_refs(self) -> "Module":
        """Every ``BeforeLesson`` / ``AfterLesson`` ref must name a lesson
        that exists in ``self.lessons``. Catches typos at parse time
        rather than as a silent placement failure at render time."""
        lesson_ids = {lesson.id for lesson in self.lessons}
        for assessment in self.assessments:
            ref_id: str | None = None
            if isinstance(assessment.position, BeforeLesson):
                ref_id = assessment.position.before_lesson
            elif isinstance(assessment.position, AfterLesson):
                ref_id = assessment.position.after_lesson
            if ref_id is not None and ref_id not in lesson_ids:
                raise ValueError(
                    f"Module `{self.id}` assessment role=`{assessment.role}` "
                    f"references unknown lesson id `{ref_id}`."
                )
        return self


class LockingConfig(StrictModel):
    """Curriculum-level content locking configuration."""

    sequential: bool = False
    lesson_sequential: bool = False


class CurriculumDef(StrictModel):
    title: str
    description: str = ""
    locking: LockingConfig = Field(default_factory=LockingConfig)
    meta: CurriculumMeta | None = None
    modules: list[Module]

    @model_validator(mode="after")
    def check_has_modules(self) -> "CurriculumDef":
        if not self.modules:
            raise ValueError("Curriculum must contain at least one module.")
        return self

    @model_validator(mode="after")
    def check_unique_ids(self) -> "CurriculumDef":
        module_ids: list[str] = [m.id for m in self.modules]
        seen_module_ids: set[str] = set()
        for mid in module_ids:
            if mid in seen_module_ids:
                raise ValueError(f"Duplicate module id `{mid}`.")
            seen_module_ids.add(mid)

        seen_lesson_ids: set[str] = set()
        for module in self.modules:
            for lesson in module.lessons:
                if lesson.id in seen_lesson_ids:
                    raise ValueError(
                        f"Duplicate lesson id `{lesson.id}` "
                        f"(in module `{module.id}`)."
                    )
                seen_lesson_ids.add(lesson.id)

        return self


class CurriculumV1(StrictModel):
    version: str
    curriculum: CurriculumDef
