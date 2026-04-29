# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""SvelteKit smoke test — full build pipeline through pnpm build.

These tests are marked with @pytest.mark.smoke and are intentionally slow
(they run pnpm install + vite build). They are skipped when the
SKIP_SMOKE environment variable is set to any non-empty value.
"""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from learningfoundry.pipeline import run_build

FIXTURES_DIR = Path(__file__).parent / "fixtures"
VALID_CURRICULUM = FIXTURES_DIR / "valid-curriculum.yml"

pytestmark = pytest.mark.smoke


def _stub_providers() -> tuple[MagicMock, MagicMock, MagicMock]:
    quiz = MagicMock()
    quiz.compile_assessment.return_value = {"quizName": "q", "questions": []}
    exercise = MagicMock()
    exercise.compile_exercise.return_value = {"status": "stub"}
    vis = MagicMock()
    vis.compile_visualization.return_value = {"status": "stub"}
    return quiz, exercise, vis


@pytest.fixture(scope="module")
def built_app(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the SvelteKit app once for the whole module."""
    if os.environ.get("SKIP_SMOKE"):
        pytest.skip("SKIP_SMOKE is set")

    quiz, exercise, vis = _stub_providers()
    out = tmp_path_factory.mktemp("sveltekit_smoke")

    run_build(
        VALID_CURRICULUM,
        out,
        base_dir=FIXTURES_DIR,
        quiz_provider=quiz,
        exercise_provider=exercise,
        visualization_provider=vis,
    )
    return out


@pytest.fixture(scope="module")
def installed_app(built_app: Path) -> Path:
    """Run pnpm install in the built app directory."""
    result = subprocess.run(
        ["pnpm", "install"],
        cwd=built_app,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"pnpm install failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    return built_app


@pytest.fixture(scope="module")
def compiled_app(installed_app: Path) -> Path:
    """Run pnpm build in the installed app directory."""
    result = subprocess.run(
        ["pnpm", "build"],
        cwd=installed_app,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"pnpm build failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    return installed_app


class TestSvelteKitSmokeBuild:
    def test_pnpm_install_succeeds(self, installed_app: Path) -> None:
        assert (installed_app / "node_modules").exists()

    def test_pnpm_build_produces_build_dir(self, compiled_app: Path) -> None:
        assert (compiled_app / "build").exists()
        assert (compiled_app / "build").is_dir()

    def test_build_produces_index_html(self, compiled_app: Path) -> None:
        assert (compiled_app / "build" / "index.html").exists()

    def test_curriculum_json_present_in_build(self, compiled_app: Path) -> None:
        assert (compiled_app / "build" / "curriculum.json").exists()

    def test_curriculum_json_valid_in_build(self, compiled_app: Path) -> None:
        data = json.loads(
            (compiled_app / "build" / "curriculum.json").read_text()
        )
        assert isinstance(data, dict)
        assert "modules" in data
        assert len(data["modules"]) == 2

    def test_build_contains_js_assets(self, compiled_app: Path) -> None:
        build_dir = compiled_app / "build"
        js_files = list(build_dir.rglob("*.js"))
        assert len(js_files) > 0

    def test_typography_prose_styles_in_bundled_css(
        self, compiled_app: Path
    ) -> None:
        """The `prose` class on rendered markdown (TextBlock.svelte) must
        compile into the bundled CSS so headings, lists, and code in lesson
        content render with proper typography. Regression guard for the
        missing `@tailwindcss/typography` plugin fixed in v0.32.0."""
        css_files = list((compiled_app / "build").rglob("*.css"))
        assert css_files, "no CSS files in build output"
        combined = "\n".join(f.read_text(encoding="utf-8") for f in css_files)
        assert ".prose" in combined, (
            "`.prose` class not found in bundled CSS — the "
            "@tailwindcss/typography plugin is not registered."
        )

    def test_pnpm_test_passes(self, installed_app: Path) -> None:
        """Run vitest in the installed template to catch frontend regressions
        (e.g. the navigation goto() bug fixed in v0.29.0)."""
        result = subprocess.run(
            ["pnpm", "test"],
            cwd=installed_app,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"pnpm test failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
