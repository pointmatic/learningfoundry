# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for the SvelteKit project generator."""

import json
from pathlib import Path

import pytest

from learningfoundry.exceptions import GenerationError
from learningfoundry.generator import generate_app
from learningfoundry.resolver import (
    ResolvedCurriculum,
    ResolvedLesson,
    ResolvedModule,
)

TEMPLATE_DIR = (
    Path(__file__).parent.parent / "sveltekit_template"
)


def _make_resolved() -> ResolvedCurriculum:
    return ResolvedCurriculum(
        version="1.0.0",
        title="Test Curriculum",
        description="A test curriculum.",
        modules=[
            ResolvedModule(
                id="mod-01",
                title="Module One",
                description="",
                pre_assessment=None,
                post_assessment=None,
                lessons=[
                    ResolvedLesson(
                        id="lesson-01",
                        title="Lesson One",
                        content_blocks=[],
                    )
                ],
            )
        ],
    )


class TestOutputStructure:
    def test_output_dir_is_created(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        assert out.exists()
        assert out.is_dir()

    def test_package_json_is_present(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        assert (out / "package.json").exists()

    def test_svelte_config_is_present(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        assert (out / "svelte.config.js").exists()

    def test_curriculum_json_is_present(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        assert (out / "static" / "curriculum.json").exists()


class TestCurriculumJson:
    def test_curriculum_json_is_valid_json(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        data = json.loads((out / "static" / "curriculum.json").read_text())
        assert isinstance(data, dict)

    def test_curriculum_json_version_matches(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        resolved = _make_resolved()
        generate_app(resolved, out, template_dir=TEMPLATE_DIR)
        data = json.loads((out / "static" / "curriculum.json").read_text())
        assert data["version"] == resolved.version

    def test_curriculum_json_title_matches(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        resolved = _make_resolved()
        generate_app(resolved, out, template_dir=TEMPLATE_DIR)
        data = json.loads((out / "static" / "curriculum.json").read_text())
        assert data["title"] == resolved.title

    def test_curriculum_json_modules_present(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        resolved = _make_resolved()
        generate_app(resolved, out, template_dir=TEMPLATE_DIR)
        data = json.loads((out / "static" / "curriculum.json").read_text())
        assert len(data["modules"]) == 1
        assert data["modules"][0]["id"] == "mod-01"


class TestOverwriteBehavior:
    def test_second_call_overwrites_output(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        # Modify a file to verify it gets replaced
        sentinel = out / "static" / "curriculum.json"
        sentinel.write_text("stale content")
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        data = json.loads(sentinel.read_text())
        assert data["version"] == "1.0.0"

    def test_overwrite_logs_info(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        import logging
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        with caplog.at_level(logging.INFO, logger="learningfoundry.generator"):
            generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        assert "already exists" in caplog.text
        # Message should reflect the new preservation behaviour, not a wipe.
        assert "preserving" in caplog.text


class TestPreserveInstallState:
    """Second-build behaviour: install/build state survives regen."""

    def test_node_modules_is_preserved_across_rebuilds(
        self, tmp_path: Path
    ) -> None:
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)

        # Simulate a completed `pnpm install`.
        (out / "node_modules").mkdir()
        (out / "node_modules" / "marker.txt").write_text("installed")

        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        assert (out / "node_modules" / "marker.txt").exists()
        assert (out / "node_modules" / "marker.txt").read_text() == "installed"

    def test_pnpm_lock_is_preserved_across_rebuilds(
        self, tmp_path: Path
    ) -> None:
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)

        (out / "pnpm-lock.yaml").write_text("lockfileVersion: 9.0\n")

        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        assert (out / "pnpm-lock.yaml").read_text() == "lockfileVersion: 9.0\n"

    def test_build_dir_is_preserved_across_rebuilds(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)

        (out / "build").mkdir()
        (out / "build" / "index.html").write_text("<html>cached</html>")

        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        assert (out / "build" / "index.html").read_text() == "<html>cached</html>"

    def test_svelte_kit_dir_is_preserved_across_rebuilds(
        self, tmp_path: Path
    ) -> None:
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)

        (out / ".svelte-kit").mkdir()
        (out / ".svelte-kit" / "marker.txt").write_text("kit-cache")

        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        assert (out / ".svelte-kit" / "marker.txt").read_text() == "kit-cache"

    def test_template_files_still_refresh_when_state_preserved(
        self, tmp_path: Path
    ) -> None:
        """Curriculum.json updates on rebuild even when node_modules persists."""
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        (out / "node_modules").mkdir()
        (out / "node_modules" / "marker.txt").write_text("installed")

        # Tamper with curriculum.json — it should be replaced on rebuild.
        (out / "static" / "curriculum.json").write_text("STALE")

        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        data = json.loads((out / "static" / "curriculum.json").read_text())
        assert data["version"] == "1.0.0"
        # And node_modules is still there.
        assert (out / "node_modules" / "marker.txt").exists()


class TestCheckDepState:
    """Detection of whether `pnpm install` is needed after a build."""

    def test_first_build_when_no_node_modules(self, tmp_path: Path) -> None:
        from learningfoundry.generator import DepState, check_dep_state

        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        assert check_dep_state(out) is DepState.FIRST_BUILD

    def test_unchanged_when_all_declared_deps_installed(
        self, tmp_path: Path
    ) -> None:
        from learningfoundry.generator import DepState, check_dep_state

        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)

        # Fake a node_modules with every declared dep present.
        pkg = json.loads((out / "package.json").read_text())
        deps = {
            **(pkg.get("dependencies") or {}),
            **(pkg.get("devDependencies") or {}),
        }
        nm = out / "node_modules"
        nm.mkdir()
        for name in deps:
            # Handle scoped packages like @sveltejs/kit
            (nm / name).mkdir(parents=True, exist_ok=True)
            (nm / name / "package.json").write_text("{}")

        assert check_dep_state(out) is DepState.UNCHANGED

    def test_changed_when_a_declared_dep_is_missing(
        self, tmp_path: Path
    ) -> None:
        from learningfoundry.generator import DepState, check_dep_state

        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)

        # node_modules exists but is empty — every declared dep is "missing".
        (out / "node_modules").mkdir()
        assert check_dep_state(out) is DepState.CHANGED

    def test_changed_when_package_json_is_malformed(self, tmp_path: Path) -> None:
        from learningfoundry.generator import DepState, check_dep_state

        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        (out / "node_modules").mkdir()
        (out / "package.json").write_text("not json {")

        assert check_dep_state(out) is DepState.CHANGED


class TestMissingTemplate:
    def test_missing_template_raises_generation_error(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        with pytest.raises(GenerationError, match="template directory not found"):
            generate_app(
                _make_resolved(),
                out,
                template_dir=tmp_path / "nonexistent_template",
            )
