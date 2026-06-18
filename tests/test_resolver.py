# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for the content resolver."""

import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

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
            assessment_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert isinstance(result, ResolvedCurriculum)

    def test_resolved_curriculum_has_modules(self, tmp_path: Path) -> None:
        c = _make_curriculum()
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert len(result.modules) == 1
        assert isinstance(result.modules[0], ResolvedModule)

    def test_resolved_module_has_lessons(self, tmp_path: Path) -> None:
        c = _make_curriculum()
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert len(result.modules[0].lessons) == 1
        assert isinstance(result.modules[0].lessons[0], ResolvedLesson)

    def test_metadata_preserved(self, tmp_path: Path) -> None:
        c = _make_curriculum()
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert result.version == "1.0.0"
        assert result.title == "Test"

    def test_curriculum_meta_round_trips(self, tmp_path: Path) -> None:
        """Story J.h — curriculum-level `meta` flows through the resolver
        into the JSON-serialised payload, including the `extra="allow"`
        round-trip for author-defined extras."""
        c = CurriculumV1.model_validate({
            "version": "1.0.0",
            "curriculum": {
                "title": "Test",
                "meta": {
                    "target_audience": "engineers",
                    "objectives": ["Explain backprop"],
                    "prerequisites": ["Python 3"],
                    "pedagogical_approach": "spiral",  # extra
                },
                "modules": [{
                    "id": "mod-01", "title": "M",
                    "lessons": [{"id": "lesson-01", "title": "L",
                                 "content_blocks": []}],
                }],
            },
        })
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert result.meta is not None
        assert result.meta["target_audience"] == "engineers"
        assert result.meta["objectives"] == ["Explain backprop"]
        assert result.meta["pedagogical_approach"] == "spiral"

    def test_curriculum_meta_absent_is_none(self, tmp_path: Path) -> None:
        c = _make_curriculum()
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert result.meta is None

    def test_module_description_round_trips(self, tmp_path: Path) -> None:
        """Module `description` from YAML is preserved on ResolvedModule for
        the frontend dashboard. Emitted in curriculum.json for each module."""
        c = CurriculumV1.model_validate({
            "version": "1.0.0",
            "curriculum": {
                "title": "Test",
                "modules": [
                    {
                        "id": "mod-01",
                        "title": "Module One",
                        "description": "First module.",
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
        })
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert result.modules[0].description == "First module."


class TestTextBlockResolution:
    def test_text_block_reads_markdown(self, tmp_path: Path) -> None:
        md = tmp_path / "content" / "lesson.md"
        md.parent.mkdir()
        md.write_text("# Hello\nSome content.")
        c = _curriculum_with_blocks([{"type": "text", "ref": "content/lesson.md"}])
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
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
                assessment_provider=MagicMock(),
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
                assessment_provider=MagicMock(),
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
                assessment_provider=MagicMock(),
                exercise_provider=MagicMock(),
                visualization_provider=MagicMock(),
            )
        assert "empty" in caplog.text.lower()


class TestTextBlockImageAssets:
    """Image references inside lesson markdown should be discovered by the
    resolver, copied (by the generator) to ``static/content/<hash>/``, and
    rewritten to absolute URLs in the in-memory markdown. The assets are
    aggregated and deduped on ``ResolvedCurriculum.assets``."""

    PNG = b"\x89PNG\r\nfake-bytes-for-resolver-tests"

    def test_assets_populated_on_resolved_curriculum(
        self, tmp_path: Path
    ) -> None:
        md_dir = tmp_path / "content"
        md_dir.mkdir()
        (md_dir / "lesson.md").write_text("![Alt](figure.png)")
        (md_dir / "figure.png").write_bytes(self.PNG)

        c = _curriculum_with_blocks([{"type": "text", "ref": "content/lesson.md"}])
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )

        assert len(result.assets) == 1
        assert result.assets[0].dest_relative.startswith("content/")
        assert result.assets[0].dest_relative.endswith("/figure.png")

    def test_markdown_url_rewritten_to_absolute_path(
        self, tmp_path: Path
    ) -> None:
        md_dir = tmp_path / "content"
        md_dir.mkdir()
        (md_dir / "lesson.md").write_text("![Alt](figure.png)")
        (md_dir / "figure.png").write_bytes(self.PNG)

        c = _curriculum_with_blocks([{"type": "text", "ref": "content/lesson.md"}])
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )

        rewritten = result.modules[0].lessons[0].content_blocks[0].content[
            "markdown"
        ]
        assert "(figure.png)" not in rewritten
        assert "(/content/" in rewritten
        assert "/figure.png)" in rewritten

    def test_missing_image_raises_with_lesson_location(
        self, tmp_path: Path
    ) -> None:
        md_dir = tmp_path / "content"
        md_dir.mkdir()
        (md_dir / "lesson.md").write_text("![Missing](nope.png)")

        c = _curriculum_with_blocks([{"type": "text", "ref": "content/lesson.md"}])
        with pytest.raises(ContentResolutionError) as exc_info:
            resolve_curriculum(
                c, tmp_path,
                assessment_provider=MagicMock(),
                exercise_provider=MagicMock(),
                visualization_provider=MagicMock(),
            )
        msg = str(exc_info.value)
        # Lesson location prefix is preserved through the asset error wrap.
        assert "mod-01" in msg
        assert "lesson-01" in msg
        assert "nope.png" in msg

    def test_assets_deduped_across_lessons(self, tmp_path: Path) -> None:
        # Two lessons both reference the same image; should land on the
        # ResolvedCurriculum once, not twice.
        md_dir = tmp_path / "content"
        md_dir.mkdir()
        (md_dir / "lesson-01.md").write_text("![](shared.png)")
        (md_dir / "lesson-02.md").write_text("Different text. ![](shared.png)")
        (md_dir / "shared.png").write_bytes(self.PNG)

        c = CurriculumV1.model_validate({
            "version": "1.0.0",
            "curriculum": {
                "title": "T",
                "modules": [
                    {
                        "id": "mod-01",
                        "title": "M",
                        "lessons": [
                            {
                                "id": "lesson-01",
                                "title": "L1",
                                "content_blocks": [
                                    {"type": "text", "ref": "content/lesson-01.md"}
                                ],
                            },
                            {
                                "id": "lesson-02",
                                "title": "L2",
                                "content_blocks": [
                                    {"type": "text", "ref": "content/lesson-02.md"}
                                ],
                            },
                        ],
                    }
                ],
            },
        })
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )

        assert len(result.assets) == 1


class TestVideoBlockResolution:
    def test_valid_youtube_url_resolved(self, tmp_path: Path) -> None:
        c = _curriculum_with_blocks(
            [{"type": "video", "url": "https://www.youtube.com/watch?v=abc123"}]
        )
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        block = result.modules[0].lessons[0].content_blocks[0]
        assert block.type == "video"
        assert block.content["url"] == "https://www.youtube.com/watch?v=abc123"
        assert block.content["provider"] == "youtube"
        assert block.content["extensions"] == {}

    def test_video_extensions_preserved(self, tmp_path: Path) -> None:
        c = _curriculum_with_blocks(
            [
                {
                    "type": "video",
                    "url": "https://www.youtube.com/watch?v=abc123",
                    "extensions": {
                        "chapters": [{"start_sec": 0, "title": "Intro"}],
                    },
                }
            ]
        )
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        block = result.modules[0].lessons[0].content_blocks[0]
        ext = block.content["extensions"]
        assert ext["chapters"][0]["title"] == "Intro"

    def test_invalid_youtube_url_raises_at_parse_time(self) -> None:
        with pytest.raises(ValidationError, match="YouTube"):
            _curriculum_with_blocks(
                [{"type": "video", "url": "https://vimeo.com/12345"}]
            )


class TestAssessmentBlockResolution:
    def test_delegates_to_assessment_provider(self, tmp_path: Path) -> None:
        mock_quiz = MagicMock()
        mock_quiz.compile_assessment.return_value = {
            "assessmentName": "q1",
            "questions": [],
        }
        c = _curriculum_with_blocks(
            [{"type": "assessment", "source": "quizazz", "ref": "assessments/q.yml"}]
        )
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=mock_quiz,
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        mock_quiz.compile_assessment.assert_called_once_with(
            Path("assessments/q.yml"), tmp_path
        )
        block = result.modules[0].lessons[0].content_blocks[0]
        assert block.type == "assessment"
        assert block.content["assessmentName"] == "q1"

    def test_provider_error_wrapped_with_location(self, tmp_path: Path) -> None:
        mock_quiz = MagicMock()
        mock_quiz.compile_assessment.side_effect = RuntimeError("bad quiz")
        c = _curriculum_with_blocks(
            [{"type": "assessment", "source": "quizazz", "ref": "assessments/q.yml"}]
        )
        with pytest.raises(ContentResolutionError, match="lesson-01"):
            resolve_curriculum(
                c, tmp_path,
                assessment_provider=mock_quiz,
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
            assessment_provider=MagicMock(),
            exercise_provider=mock_ex,
            visualization_provider=MagicMock(),
        )
        mock_ex.compile_exercise.assert_called_once_with(
            Path("exercises/e.yml"), tmp_path
        )
        block = result.modules[0].lessons[0].content_blocks[0]
        assert block.type == "exercise"


class TestExerciseStatusSwitch:
    """Story K.d — the resolver owns the `status` switch: `stub` emits the
    placeholder via `stub_exercise` (no provider call, no nbfoundry import);
    `ready` (and the default) compiles via the injected provider and fails
    loud — never silently degrading to a placeholder."""

    def test_stub_status_emits_placeholder_without_provider_call(
        self, tmp_path: Path
    ) -> None:
        from learningfoundry.integrations.nbfoundry_stub import stub_exercise

        mock_ex = MagicMock()
        c = _curriculum_with_blocks(
            [
                {
                    "type": "exercise",
                    "source": "nbfoundry",
                    "ref": "exercises/e.yml",
                    "status": "stub",
                }
            ]
        )
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=mock_ex,
            visualization_provider=MagicMock(),
        )
        mock_ex.compile_exercise.assert_not_called()
        block = result.modules[0].lessons[0].content_blocks[0]
        # The resolver injects the curriculum-level `id` (Story K.f) so the
        # frontend has the asset-URL namespace + progress key; otherwise the
        # stub content is the shared placeholder.
        assert block.content == {**stub_exercise(Path("exercises/e.yml")), "id": "e"}

    def test_stub_status_never_imports_nbfoundry_with_default_provider(
        self, tmp_path: Path
    ) -> None:
        # No injected provider → default NbfoundryProvider. An all-stub
        # curriculum resolves cleanly even though nbfoundry is not installed,
        # because the stub path makes no provider call (and thus no import).
        c = _curriculum_with_blocks(
            [
                {
                    "type": "exercise",
                    "source": "nbfoundry",
                    "ref": "exercises/e.yml",
                    "status": "stub",
                }
            ]
        )
        result = resolve_curriculum(c, tmp_path, assessment_provider=MagicMock())
        block = result.modules[0].lessons[0].content_blocks[0]
        assert block.content["status"] == "stub"

    def test_ready_status_invokes_provider(self, tmp_path: Path) -> None:
        mock_ex = MagicMock()
        mock_ex.compile_exercise.return_value = {"status": "ready", "title": "Ex"}
        c = _curriculum_with_blocks(
            [
                {
                    "type": "exercise",
                    "source": "nbfoundry",
                    "ref": "exercises/e.yml",
                    "status": "ready",
                }
            ]
        )
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=mock_ex,
            visualization_provider=MagicMock(),
        )
        mock_ex.compile_exercise.assert_called_once_with(
            Path("exercises/e.yml"), tmp_path
        )
        block = result.modules[0].lessons[0].content_blocks[0]
        assert block.content["status"] == "ready"

    def test_default_status_invokes_provider(self, tmp_path: Path) -> None:
        # No `status` key → defaults to `ready` → provider is called.
        mock_ex = MagicMock()
        mock_ex.compile_exercise.return_value = {"status": "ready"}
        c = _curriculum_with_blocks(
            [{"type": "exercise", "source": "nbfoundry", "ref": "exercises/e.yml"}]
        )
        resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=mock_ex,
            visualization_provider=MagicMock(),
        )
        mock_ex.compile_exercise.assert_called_once()

    def test_ready_block_failure_fails_loud_no_stub_fallback(
        self, tmp_path: Path
    ) -> None:
        # A `ready` exercise whose ref can't be compiled must surface the
        # error — not silently fall back to a placeholder (OR-1 fail-fast).
        mock_ex = MagicMock()
        mock_ex.compile_exercise.side_effect = FileNotFoundError(
            "exercises/e.yml missing"
        )
        c = _curriculum_with_blocks(
            [
                {
                    "type": "exercise",
                    "source": "nbfoundry",
                    "ref": "exercises/e.yml",
                    "status": "ready",
                }
            ]
        )
        with pytest.raises(ContentResolutionError):
            resolve_curriculum(
                c, tmp_path,
                assessment_provider=MagicMock(),
                exercise_provider=mock_ex,
                visualization_provider=MagicMock(),
            )

    def test_default_provider_is_nbfoundry_provider_not_stub(
        self, tmp_path: Path
    ) -> None:
        # With the default provider and a `ready` block, compilation routes
        # to the real NbfoundryProvider. nbfoundry is not installed, so it
        # raises ImportError (wrapped) — proving the default is no longer the
        # stub (which would have silently produced a placeholder).
        c = _curriculum_with_blocks(
            [
                {
                    "type": "exercise",
                    "source": "nbfoundry",
                    "ref": "exercises/e.yml",
                    "status": "ready",
                }
            ]
        )
        with pytest.raises(ContentResolutionError, match="nbfoundry"):
            resolve_curriculum(c, tmp_path, assessment_provider=MagicMock())


class TestExerciseAssetStaging:
    """Story K.e — a compiled `ready` exercise's `assets: list[str]` are
    staged into `static/exercises/<id>/<path>` via the shared assets_by_dest
    aggregator (deduped on `dest_relative`). Stub exercises carry no assets
    and stage nothing."""

    def _exercise(self, **extra: object) -> dict:  # type: ignore[type-arg]
        block = {"type": "exercise", "source": "nbfoundry", "ref": "exercises/e.yml"}
        block.update(extra)
        return block

    def test_ready_exercise_assets_emit_namespaced_records(
        self, tmp_path: Path
    ) -> None:
        mock_ex = MagicMock()
        mock_ex.compile_exercise.return_value = {
            "status": "ready",
            "assets": ["data/img.png", "weights/model.pt"],
        }
        c = _curriculum_with_blocks([self._exercise(status="ready")])
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=mock_ex,
            visualization_provider=MagicMock(),
        )
        by_dest = {a.dest_relative: a for a in result.assets}
        assert set(by_dest) == {
            "exercises/e/data/img.png",
            "exercises/e/weights/model.pt",
        }
        assert by_dest["exercises/e/data/img.png"].source == tmp_path / "data/img.png"

    def test_explicit_id_namespaces_assets(self, tmp_path: Path) -> None:
        mock_ex = MagicMock()
        mock_ex.compile_exercise.return_value = {
            "status": "ready",
            "assets": ["fig.png"],
        }
        c = _curriculum_with_blocks([self._exercise(id="custom", status="ready")])
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=mock_ex,
            visualization_provider=MagicMock(),
        )
        assert {a.dest_relative for a in result.assets} == {"exercises/custom/fig.png"}

    def test_ready_exercise_without_assets_stages_nothing(
        self, tmp_path: Path
    ) -> None:
        mock_ex = MagicMock()
        mock_ex.compile_exercise.return_value = {"status": "ready"}  # no `assets` key
        c = _curriculum_with_blocks([self._exercise()])
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=mock_ex,
            visualization_provider=MagicMock(),
        )
        assert result.assets == []

    def test_stub_exercise_stages_nothing(self, tmp_path: Path) -> None:
        c = _curriculum_with_blocks([self._exercise(status="stub")])
        result = resolve_curriculum(c, tmp_path, assessment_provider=MagicMock())
        assert result.assets == []

    def test_same_asset_listed_twice_is_deduped(self, tmp_path: Path) -> None:
        mock_ex = MagicMock()
        mock_ex.compile_exercise.return_value = {
            "status": "ready",
            "assets": ["fig.png", "fig.png"],
        }
        c = _curriculum_with_blocks([self._exercise(status="ready")])
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=mock_ex,
            visualization_provider=MagicMock(),
        )
        assert len(result.assets) == 1
        assert result.assets[0].dest_relative == "exercises/e/fig.png"


class TestExerciseIdInResolvedContent:
    """Story K.f — the resolver injects the curriculum-level exercise `id`
    into the resolved content dict (both stub and ready), so the frontend can
    compose `/exercises/<id>/<path>` asset URLs and use `id` as the
    `exerciseRef` progress key. `id` is authoritative (handles explicit-id
    overrides nbfoundry's compiled dict doesn't know about)."""

    def test_ready_content_carries_auto_derived_id(self, tmp_path: Path) -> None:
        mock_ex = MagicMock()
        mock_ex.compile_exercise.return_value = {"status": "ready", "title": "Ex"}
        c = _curriculum_with_blocks(
            [{"type": "exercise", "source": "nbfoundry", "ref": "exercises/e.yml"}]
        )
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=mock_ex,
            visualization_provider=MagicMock(),
        )
        assert result.modules[0].lessons[0].content_blocks[0].content["id"] == "e"

    def test_ready_content_carries_explicit_id(self, tmp_path: Path) -> None:
        mock_ex = MagicMock()
        mock_ex.compile_exercise.return_value = {"status": "ready"}
        c = _curriculum_with_blocks(
            [
                {
                    "type": "exercise",
                    "source": "nbfoundry",
                    "ref": "exercises/e.yml",
                    "id": "custom",
                }
            ]
        )
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=mock_ex,
            visualization_provider=MagicMock(),
        )
        assert result.modules[0].lessons[0].content_blocks[0].content["id"] == "custom"

    def test_stub_content_carries_id(self, tmp_path: Path) -> None:
        c = _curriculum_with_blocks(
            [
                {
                    "type": "exercise",
                    "source": "nbfoundry",
                    "ref": "exercises/e.yml",
                    "status": "stub",
                }
            ]
        )
        result = resolve_curriculum(c, tmp_path, assessment_provider=MagicMock())
        assert result.modules[0].lessons[0].content_blocks[0].content["id"] == "e"


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
            assessment_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=mock_vis,
        )
        mock_vis.compile_visualization.assert_called_once_with(
            Path("visualizations/v.yml"), tmp_path
        )
        block = result.modules[0].lessons[0].content_blocks[0]
        assert block.type == "visualization"


class TestAssessmentResolution:
    """Story J.e — assessments[] replaces pre/post; resolver materializes
    them in canonical placement order."""

    def _build_curriculum(self, assessments: list[dict]) -> CurriculumV1:  # type: ignore[type-arg]
        return CurriculumV1.model_validate({
            "version": "1.0.0",
            "curriculum": {
                "title": "T",
                "modules": [
                    {
                        "id": "mod-01",
                        "title": "M",
                        "assessments": assessments,
                        "lessons": [
                            {
                                "id": "lesson-01",
                                "title": "L1",
                                "content_blocks": [],
                            },
                            {
                                "id": "lesson-02",
                                "title": "L2",
                                "content_blocks": [],
                            },
                        ],
                    }
                ],
            },
        })

    def test_before_lessons_resolves_to_first_position(
        self, tmp_path: Path
    ) -> None:
        mock_quiz = MagicMock()
        mock_quiz.compile_assessment.return_value = {"assessmentName": "pre"}
        curriculum = self._build_curriculum([{
            "role": "pre",
            "position": "before_lessons",
            "source": "quizazz",
            "ref": "assessments/pre.yml",
        }])
        result = resolve_curriculum(
            curriculum, tmp_path,
            assessment_provider=mock_quiz,
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assessments = result.modules[0].assessments
        assert len(assessments) == 1
        assert assessments[0].role == "pre"
        assert assessments[0].position == "before_lessons"
        assert assessments[0].content == {"assessmentName": "pre"}

    def test_after_lessons_resolves_to_last_position(
        self, tmp_path: Path
    ) -> None:
        mock_quiz = MagicMock()
        mock_quiz.compile_assessment.return_value = {"assessmentName": "post"}
        curriculum = self._build_curriculum([{
            "role": "post",
            "position": "after_lessons",
            "source": "quizazz",
            "ref": "assessments/post.yml",
            "pass_threshold": 0.8,
        }])
        result = resolve_curriculum(
            curriculum, tmp_path,
            assessment_provider=mock_quiz,
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert result.modules[0].assessments[0].pass_threshold == 0.8

    def test_resolved_order_interleaves_lesson_anchored_assessments(
        self, tmp_path: Path
    ) -> None:
        # Author order intentionally NOT canonical; resolver must reorder
        # to: before_lessons, before_lesson:lesson-01, after_lesson:lesson-01,
        # before_lesson:lesson-02, after_lesson:lesson-02, after_lessons.
        mock_quiz = MagicMock()
        mock_quiz.compile_assessment.return_value = {"assessmentName": "stub"}
        curriculum = self._build_curriculum([
            {"role": "post", "position": "after_lessons",
             "source": "quizazz", "ref": "x.yml"},
            {"role": "practice-2-after", "position": {"after_lesson": "lesson-02"},
             "source": "quizazz", "ref": "x.yml"},
            {"role": "pre", "position": "before_lessons",
             "source": "quizazz", "ref": "x.yml"},
            {"role": "practice-1-before", "position": {"before_lesson": "lesson-01"},
             "source": "quizazz", "ref": "x.yml"},
            {"role": "practice-1-after", "position": {"after_lesson": "lesson-01"},
             "source": "quizazz", "ref": "x.yml"},
        ])
        result = resolve_curriculum(
            curriculum, tmp_path,
            assessment_provider=mock_quiz,
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        roles = [a.role for a in result.modules[0].assessments]
        assert roles == [
            "pre",
            "practice-1-before",
            "practice-1-after",
            "practice-2-after",
            "post",
        ]

    def test_position_serialized_as_jsonable(self, tmp_path: Path) -> None:
        mock_quiz = MagicMock()
        mock_quiz.compile_assessment.return_value = {}
        curriculum = self._build_curriculum([
            {"role": "pre", "position": "before_lessons",
             "source": "quizazz", "ref": "x.yml"},
            {"role": "practice", "position": {"before_lesson": "lesson-02"},
             "source": "quizazz", "ref": "x.yml"},
            {"role": "post", "position": {"after_lesson": "lesson-02"},
             "source": "quizazz", "ref": "x.yml"},
        ])
        result = resolve_curriculum(
            curriculum, tmp_path,
            assessment_provider=mock_quiz,
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        positions = [a.position for a in result.modules[0].assessments]
        assert positions == [
            "before_lessons",
            {"before_lesson": "lesson-02"},
            {"after_lesson": "lesson-02"},
        ]

    def test_assessment_error_raises_content_resolution_error(
        self, tmp_path: Path
    ) -> None:
        mock_quiz = MagicMock()
        mock_quiz.compile_assessment.side_effect = RuntimeError("broken")
        curriculum = self._build_curriculum([{
            "role": "pre",
            "position": "before_lessons",
            "source": "quizazz",
            "ref": "assessments/pre.yml",
        }])
        with pytest.raises(ContentResolutionError, match="role=`pre`"):
            resolve_curriculum(
                curriculum, tmp_path,
                assessment_provider=mock_quiz,
                exercise_provider=MagicMock(),
                visualization_provider=MagicMock(),
            )

    def test_no_assessments_yields_empty_list(self, tmp_path: Path) -> None:
        curriculum = self._build_curriculum([])
        result = resolve_curriculum(
            curriculum, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert result.modules[0].assessments == []


class TestLockingResolution:
    def test_locking_fields_in_resolved_curriculum(self, tmp_path: Path) -> None:
        (tmp_path / "l.md").write_text("hi")
        c = CurriculumV1.model_validate({
            "version": "1.0.0",
            "curriculum": {
                "title": "T",
                "locking": {"sequential": True, "lesson_sequential": True},
                "modules": [{
                    "id": "mod-01",
                    "title": "M",
                    "locked": False,
                    "lessons": [{
                        "id": "lesson-01",
                        "title": "L",
                        "unlock_module_on_complete": True,
                        "content_blocks": [{"type": "text", "ref": "l.md"}],
                    }],
                }],
            },
        })
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert result.locking == {"sequential": True, "lesson_sequential": True}
        assert result.modules[0].locked is False
        assert result.modules[0].lessons[0].unlock_module_on_complete is True

    def test_assessment_pass_threshold_propagated(self, tmp_path: Path) -> None:
        mock_quiz = MagicMock()
        mock_quiz.compile_assessment.return_value = {
            "assessmentName": "q",
            "questions": [],
        }
        c = CurriculumV1.model_validate({
            "version": "1.0.0",
            "curriculum": {
                "title": "T",
                "modules": [{
                    "id": "mod-01",
                    "title": "M",
                    "lessons": [{
                        "id": "lesson-01",
                        "title": "L",
                        "content_blocks": [{
                            "type": "assessment",
                            "source": "quizazz",
                            "ref": "q.yml",
                            "pass_threshold": 0.8,
                        }],
                    }],
                }],
            },
        })
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=mock_quiz,
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        quiz_content = result.modules[0].lessons[0].content_blocks[0].content
        assert quiz_content["pass_threshold"] == 0.8

    def test_unlock_module_on_complete_defaults_false(self, tmp_path: Path) -> None:
        (tmp_path / "l.md").write_text("hi")
        c = _curriculum_with_blocks([{"type": "text", "ref": "l.md"}])
        result = resolve_curriculum(
            c, tmp_path,
            assessment_provider=MagicMock(),
            exercise_provider=MagicMock(),
            visualization_provider=MagicMock(),
        )
        assert result.modules[0].lessons[0].unlock_module_on_complete is False
