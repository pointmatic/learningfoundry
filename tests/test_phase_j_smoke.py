# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Cross-cutting Phase J smoke (Story J.g).

Every Phase J affordance — lesson and module ``meta``, all three tutorial
directives, all three assessment roles with mixed positions, and the
``duration_minutes`` aggregate — composes cleanly through parse → resolve
→ generate end-to-end. Per-feature tests are narrow by design; this
single fixture is the integration anchor that catches "feature A and
feature B both work in isolation but conflict together" regressions.

Stays in the regular pytest path (no ``smoke`` marker, no pnpm/vite
dependency). DOM-rendering of each affordance is covered by the vitest
suite under ``sveltekit_template/src/lib/components/`` and
``sveltekit_template/src/lib/utils/``.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

from learningfoundry.pipeline import run_build

FIXTURES_DIR = Path(__file__).parent / "fixtures"
CURRICULUM = FIXTURES_DIR / "phase-j-curriculum.yml"
CONTENT_DIR = FIXTURES_DIR / "phase-j-content"


def _stub_providers() -> tuple[MagicMock, MagicMock, MagicMock]:
    quiz = MagicMock()
    quiz.compile_assessment.side_effect = lambda ref, _base: {
        "quizName": Path(ref).stem,
        "questions": [],
    }
    exercise = MagicMock()
    exercise.compile_exercise.return_value = {"status": "stub"}
    vis = MagicMock()
    vis.compile_visualization.return_value = {"status": "stub"}
    return quiz, exercise, vis


def _build(tmp_path: Path) -> dict:  # type: ignore[type-arg]
    """Run the pipeline, then read back the generated curriculum.json.

    The fixture's content/ directory is named ``phase-j-content/`` so the
    YAML refs (``content/mod-01/lesson-01.md``) resolve relative to a
    custom base — copy the content tree into the build root so relative
    paths line up with how ``learningfoundry build`` is normally
    invoked.
    """
    build_root = tmp_path / "build_root"
    build_root.mkdir()
    # Copy the curriculum file and its content/ tree side-by-side.
    (build_root / "curriculum.yml").write_bytes(CURRICULUM.read_bytes())
    import shutil

    shutil.copytree(CONTENT_DIR, build_root / "content")

    quiz, exercise, vis = _stub_providers()
    run_build(
        build_root / "curriculum.yml",
        tmp_path / "out",
        base_dir=build_root,
        quiz_provider=quiz,
        exercise_provider=exercise,
        visualization_provider=vis,
    )
    return json.loads(  # type: ignore[no-any-return]
        (tmp_path / "out" / "static" / "curriculum.json").read_text()
    )


class TestPhaseJSmoke:
    def test_module_meta_present(self, tmp_path: Path) -> None:
        data = _build(tmp_path)
        meta = data["modules"][0]["meta"]
        assert meta["theme"] == "Why convolutions exist"
        assert meta["big_problem"].startswith("Fully-connected")
        assert "Explain why FC nets fail on images" in meta["objectives"]
        assert meta["target_audience"].startswith("Intermediate Python")

    def test_lesson_meta_with_hook_present(self, tmp_path: Path) -> None:
        data = _build(tmp_path)
        lesson = data["modules"][0]["lessons"][0]
        assert lesson["meta"]["role"] == "opener"
        assert lesson["meta"]["hook"]["tagline"].startswith(
            "What if your first layer of vision"
        )
        assert lesson["meta"]["introduces"] == [
            "receptive_field",
            "simple_cells",
        ]

    def test_total_duration_minutes_aggregates(self, tmp_path: Path) -> None:
        data = _build(tmp_path)
        # 15 (lesson-01) + 30 (lesson-02) = 45.
        assert data["total_duration_minutes"] == 45

    def test_directive_markdown_survives_in_curriculum_json(
        self, tmp_path: Path
    ) -> None:
        data = _build(tmp_path)
        lesson_blocks = {
            lesson["id"]: lesson["content_blocks"]
            for lesson in data["modules"][0]["lessons"]
        }
        l1 = lesson_blocks["lesson-01"][0]["content"]["markdown"]
        l2 = lesson_blocks["lesson-02"][0]["content"]["markdown"]
        # Story J.d.1 — directive opens travel through to the markdown
        # source so the marked extension can render them at runtime.
        assert "::: worked-example" in l1
        assert "::: faded-example" in l2
        assert "::: independent-practice" in l2

    def test_all_three_assessment_roles_in_resolved_order(
        self, tmp_path: Path
    ) -> None:
        data = _build(tmp_path)
        assessments = data["modules"][0]["assessments"]
        roles = [a["role"] for a in assessments]
        # Resolver canonical order: before_lessons → before_lesson:lesson-02
        # → after_lessons. The fixture has no after_lesson entries.
        assert roles == ["pre", "practice", "post"]

    def test_assessment_positions_serialised_jsonable(
        self, tmp_path: Path
    ) -> None:
        data = _build(tmp_path)
        positions = [a["position"] for a in data["modules"][0]["assessments"]]
        assert positions == [
            "before_lessons",
            {"before_lesson": "lesson-02"},
            "after_lessons",
        ]

    def test_assessment_pass_thresholds_pass_through(
        self, tmp_path: Path
    ) -> None:
        data = _build(tmp_path)
        thresholds = [
            a["pass_threshold"] for a in data["modules"][0]["assessments"]
        ]
        assert thresholds == [None, 0.7, 0.8]

    def test_assessment_content_resolved(self, tmp_path: Path) -> None:
        data = _build(tmp_path)
        names = [
            a["content"]["quizName"] for a in data["modules"][0]["assessments"]
        ]
        # Each ref name is the YAML stem from the fixture.
        assert names == [
            "mod-01-pre",
            "mod-01-practice",
            "mod-01-post",
        ]

    def test_legacy_pre_post_fields_absent(self, tmp_path: Path) -> None:
        # Story J.e — clean removal regression check on the composed shape.
        data = _build(tmp_path)
        mod = data["modules"][0]
        assert "pre_assessment" not in mod
        assert "post_assessment" not in mod
