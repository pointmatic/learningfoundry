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
    Path(__file__).parent.parent
    / "src"
    / "learningfoundry"
    / "sveltekit_template"
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
                locked=None,
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


class TestImageAssetCopy:
    """Image assets carried on ResolvedCurriculum.assets must land on disk
    under ``static/<dest_relative>`` and must not appear in
    curriculum.json (the SvelteKit frontend has no use for the source paths
    of the original files)."""

    PNG = b"\x89PNG\r\nfake-bytes-for-generator-tests"

    def _make_resolved_with_asset(self, source: Path) -> ResolvedCurriculum:
        from learningfoundry.asset_resolver import Asset

        resolved = _make_resolved()
        resolved.assets = [
            Asset(source=source, dest_relative="content/abc123def456/figure.png")
        ]
        return resolved

    def test_asset_is_copied_into_static(self, tmp_path: Path) -> None:
        source = tmp_path / "src" / "figure.png"
        source.parent.mkdir()
        source.write_bytes(self.PNG)

        out = tmp_path / "app"
        generate_app(
            self._make_resolved_with_asset(source),
            out,
            template_dir=TEMPLATE_DIR,
        )

        dest = out / "static" / "content" / "abc123def456" / "figure.png"
        assert dest.is_file()
        assert dest.read_bytes() == self.PNG

    def test_assets_are_excluded_from_curriculum_json(
        self, tmp_path: Path
    ) -> None:
        source = tmp_path / "figure.png"
        source.write_bytes(self.PNG)

        out = tmp_path / "app"
        generate_app(
            self._make_resolved_with_asset(source),
            out,
            template_dir=TEMPLATE_DIR,
        )

        data = json.loads((out / "static" / "curriculum.json").read_text())
        assert "assets" not in data, (
            "Asset records carry on-disk Paths and are not for the frontend"
        )

    def test_no_assets_means_no_static_content_dir(
        self, tmp_path: Path
    ) -> None:
        # A curriculum with no images must not create an empty
        # static/content/ directory.
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        assert not (out / "static" / "content").exists()

    def test_rebuild_skips_unchanged_assets(self, tmp_path: Path) -> None:
        # The destination is content-hashed, so a matching size on a hashed
        # path is a strong signal the file is identical. The generator
        # short-circuits the copy in that case.
        source = tmp_path / "figure.png"
        source.write_bytes(self.PNG)

        out = tmp_path / "app"
        resolved = self._make_resolved_with_asset(source)
        generate_app(resolved, out, template_dir=TEMPLATE_DIR)

        dest = out / "static" / "content" / "abc123def456" / "figure.png"
        first_mtime = dest.stat().st_mtime_ns

        # Sleep would be racy; just regenerate and confirm the file is
        # untouched (mtime preserved).
        generate_app(resolved, out, template_dir=TEMPLATE_DIR)
        assert dest.stat().st_mtime_ns == first_mtime


class TestStaticContentPreserved:
    """`static/content/` must be in `_PRESERVED_PATHS` so previously-copied
    assets survive a `learningfoundry build` re-run."""

    def test_static_content_listed_in_preserved_paths(self) -> None:
        from learningfoundry.generator import _PRESERVED_PATHS

        assert "static/content" in _PRESERVED_PATHS

    def test_existing_static_content_survives_rebuild(
        self, tmp_path: Path
    ) -> None:
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)

        # Simulate a previously-copied asset surviving from a prior build.
        previous = out / "static" / "content" / "deadbeef0001" / "old.png"
        previous.parent.mkdir(parents=True)
        previous.write_bytes(b"old-asset-bytes")

        # Rebuild with no assets; the existing file should still be there.
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        assert previous.is_file()
        assert previous.read_bytes() == b"old-asset-bytes"
