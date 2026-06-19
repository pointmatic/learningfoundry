# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Live integration test against the real nbfoundry package (Story K.j.3).

The rest of the suite mocks `compile_exercise`; this module exercises the
**real** nbfoundry Option-C contract end-to-end (`compile_exercise` → resolver
→ generator → notebook + manifest). It is skipped when nbfoundry is not
installed, so the mock-only suite still runs without the `[nbfoundry]` extra.
"""

import json
from pathlib import Path

import pytest

pytest.importorskip("nbfoundry")

import nbfoundry  # noqa: E402

from learningfoundry.generator import generate_app  # noqa: E402
from learningfoundry.integrations.nbfoundry import NbfoundryProvider  # noqa: E402
from learningfoundry.resolver import resolve_curriculum  # noqa: E402
from learningfoundry.schema_v1 import CurriculumV1  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
EXERCISE_REF = "sample-exercise.yml"
EXERCISE_ID = "sample-exercise"
TEMPLATE_DIR = (
    Path(__file__).parent.parent.parent
    / "src"
    / "learningfoundry"
    / "sveltekit_template"
)

_RETIRED_OPTION_B_FIELDS = (
    "sections",
    "expected_outputs",
    "submission",
    "assets",
    "instructions",
)


@pytest.fixture
def compiled() -> dict:  # type: ignore[type-arg]
    """The real nbfoundry compilation of the fixture exercise."""
    return nbfoundry.compile_exercise(Path(EXERCISE_REF), FIXTURES)


def _curriculum_with_ready_exercise() -> CurriculumV1:  # type: ignore[type-arg]
    return CurriculumV1.model_validate(
        {
            "version": "1.0.0",
            "curriculum": {
                "title": "Live nbfoundry",
                "modules": [
                    {
                        "id": "mod-01",
                        "title": "Module One",
                        "lessons": [
                            {
                                "id": "lesson-01",
                                "title": "Lesson One",
                                "content_blocks": [
                                    {
                                        "type": "exercise",
                                        "source": "nbfoundry",
                                        "ref": EXERCISE_REF,
                                        "status": "ready",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
        }
    )


class TestRealCompileExercise:
    """The published nbfoundry honors the Option-C BR-1 contract."""

    def test_returns_option_c_banner_shape(self, compiled: dict) -> None:  # type: ignore[type-arg]
        assert compiled["type"] == "exercise"
        assert compiled["source"] == "nbfoundry"
        for key in ("title", "description", "hints", "environment", "notebook_source"):
            assert key in compiled

    def test_notebook_source_is_runnable_marimo_module(
        self, compiled: dict  # type: ignore[type-arg]
    ) -> None:
        src = compiled["notebook_source"]
        assert isinstance(src, str)
        assert "import marimo" in src
        assert "marimo.App()" in src
        # Learner-runtime imports appear as source text in cells — never
        # imported by the build (the contract's torch-free codegen rule).
        assert "import torch" in src

    def test_drops_retired_option_b_fields(self, compiled: dict) -> None:  # type: ignore[type-arg]
        assert all(field not in compiled for field in _RETIRED_OPTION_B_FIELDS)


class TestEndToEndStaging:
    """A real `ready` exercise flows resolver → generator into a staged
    notebook + manifest entry."""

    def test_resolver_pulls_real_notebook_into_artifact(self) -> None:
        resolved = resolve_curriculum(
            _curriculum_with_ready_exercise(),
            FIXTURES,
            assessment_provider=None,
            exercise_provider=NbfoundryProvider(),
            visualization_provider=None,
        )
        assert len(resolved.exercises) == 1
        artifact = resolved.exercises[0]
        assert artifact.id == EXERCISE_ID
        assert "marimo.App()" in artifact.notebook_source
        assert artifact.notebook_path == f"exercises/{EXERCISE_ID}/{EXERCISE_ID}.py"
        assert artifact.mode == "edit"  # ExerciseBlock.mode default

        # The browser-facing banner content carries id/status but not the .py.
        block = resolved.modules[0].lessons[0].content_blocks[0]
        assert block.content["id"] == EXERCISE_ID
        assert block.content["status"] == "ready"
        assert "notebook_source" not in block.content

    def test_generator_writes_notebook_and_manifest(self, tmp_path: Path) -> None:
        resolved = resolve_curriculum(
            _curriculum_with_ready_exercise(),
            FIXTURES,
            assessment_provider=None,
            exercise_provider=NbfoundryProvider(),
            visualization_provider=None,
        )
        out = tmp_path / "app"
        generate_app(resolved, out, template_dir=TEMPLATE_DIR)

        notebook = out / "exercises" / EXERCISE_ID / f"{EXERCISE_ID}.py"
        assert notebook.is_file()
        assert "marimo.App()" in notebook.read_text()

        manifest = json.loads((out / "exercises-manifest.json").read_text())
        assert manifest[EXERCISE_ID]["notebook_path"] == (
            f"exercises/{EXERCISE_ID}/{EXERCISE_ID}.py"
        )
        assert manifest[EXERCISE_ID]["mode"] == "edit"
        assert manifest[EXERCISE_ID]["port"] == 2718
