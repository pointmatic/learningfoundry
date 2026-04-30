# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Pydantic models for curriculum YAML v1 schema."""

import re
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

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


class AssessmentRef(BaseModel):
    source: str
    ref: str


class TextBlock(BaseModel):
    type: Literal["text"]
    ref: str


class VideoBlock(BaseModel):
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


class QuizBlock(BaseModel):
    type: Literal["quiz"]
    source: str
    ref: str


class ExerciseBlock(BaseModel):
    type: Literal["exercise"]
    source: str
    ref: str


class VisualizationBlock(BaseModel):
    type: Literal["visualization"]
    source: str
    ref: str


ContentBlock = Annotated[
    TextBlock | VideoBlock | QuizBlock | ExerciseBlock | VisualizationBlock,
    ...,
]


class Lesson(BaseModel):
    id: str
    title: str
    content_blocks: list[ContentBlock]

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        return _validate_id(v, "lesson id")


class Module(BaseModel):
    id: str
    title: str
    description: str = ""
    pre_assessment: AssessmentRef | None = None
    post_assessment: AssessmentRef | None = None
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


class CurriculumDef(BaseModel):
    title: str
    description: str = ""
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


class CurriculumV1(BaseModel):
    version: str
    curriculum: CurriculumDef
