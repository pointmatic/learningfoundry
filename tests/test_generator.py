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

    def test_static_sql_wasm_is_preserved_across_rebuilds(
        self, tmp_path: Path
    ) -> None:
        """`static/sql-wasm.wasm` must survive `_atomic_copy` even when the
        template ships no wasm (the gitignored / clean-checkout case).

        Regression from the recording-broken-after-second-preview bug:
        `_atomic_copy` rebuilds `static/` from the template each run, and
        `static/sql-wasm.wasm` is gitignored so a clean template lacks it.
        Without this preservation the file is silently erased on every
        rebuild after pnpm's `postinstall` populated it once.
        """
        # Synthesise a "clean" template — copy the real one, then remove
        # the wasm to simulate a fresh checkout / published wheel where
        # the gitignored file is absent.
        clean_template = tmp_path / "clean-template"
        import shutil
        shutil.copytree(TEMPLATE_DIR, clean_template, symlinks=True)
        wasm_in_template = clean_template / "static" / "sql-wasm.wasm"
        if wasm_in_template.exists():
            wasm_in_template.unlink()

        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=clean_template)

        # Simulate the postinstall (or any prior provisioning step)
        # having put the wasm into the output's static dir.
        out_wasm = out / "static" / "sql-wasm.wasm"
        out_wasm.write_bytes(b"\x00asm-fake-wasm-bytes")

        # Second build with the same clean template — wasm must survive.
        generate_app(_make_resolved(), out, template_dir=clean_template)
        assert out_wasm.exists(), (
            "static/sql-wasm.wasm was erased on rebuild — the wasm asset "
            "is not in _PRESERVED_PATHS, so a clean template wipes it."
        )
        assert out_wasm.read_bytes() == b"\x00asm-fake-wasm-bytes"


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


class TestPedagogicalMetaInCurriculumJson:
    """Story J.a — `lesson.meta` and `module.meta` propagate verbatim
    into curriculum.json."""

    def _make_resolved_with_meta(self) -> ResolvedCurriculum:
        return ResolvedCurriculum(
            version="1.0.0",
            title="Test",
            description="",
            modules=[
                ResolvedModule(
                    id="mod-01",
                    title="Module One",
                    description="",
                    locked=None,
                    meta={
                        "theme": "Why convolutions exist",
                        "objectives": ["Explain weight sharing"],
                        "big_problem": None,
                        "experiential_summary": None,
                        "target_audience": None,
                    },
                    lessons=[
                        ResolvedLesson(
                            id="lesson-01",
                            title="L",
                            meta={
                                "role": "opener",
                                "hook": {
                                    "tagline": "What if vision was a flashlight?",
                                    "image_prompt": None,
                                },
                                "introduces": ["receptive_field"],
                                "reinforces": [],
                                "duration_minutes": 15,
                            },
                            content_blocks=[],
                        )
                    ],
                )
            ],
        )

    def test_lesson_meta_emitted_verbatim(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(
            self._make_resolved_with_meta(), out, template_dir=TEMPLATE_DIR
        )
        data = json.loads((out / "static" / "curriculum.json").read_text())
        lesson = data["modules"][0]["lessons"][0]
        assert lesson["meta"]["role"] == "opener"
        assert lesson["meta"]["hook"]["tagline"] == (
            "What if vision was a flashlight?"
        )
        assert lesson["meta"]["introduces"] == ["receptive_field"]
        assert lesson["meta"]["duration_minutes"] == 15

    def test_module_meta_emitted_verbatim(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(
            self._make_resolved_with_meta(), out, template_dir=TEMPLATE_DIR
        )
        data = json.loads((out / "static" / "curriculum.json").read_text())
        module = data["modules"][0]
        assert module["meta"]["theme"] == "Why convolutions exist"
        assert module["meta"]["objectives"] == ["Explain weight sharing"]

    def test_meta_absent_is_null(self, tmp_path: Path) -> None:
        # Curriculum without meta — JSON contains `"meta": null`.
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        data = json.loads((out / "static" / "curriculum.json").read_text())
        assert data["modules"][0]["meta"] is None
        assert data["modules"][0]["lessons"][0]["meta"] is None


class TestAssessmentsArrayInCurriculumJson:
    """Story J.e — `module.assessments[]` lands in `curriculum.json` in
    resolved order with role / position / source / ref / pass_threshold /
    content; old `pre_assessment` / `post_assessment` fields are gone."""

    def _make_with_assessments(self) -> ResolvedCurriculum:
        from learningfoundry.resolver import ResolvedAssessment

        return ResolvedCurriculum(
            version="1.0.0",
            title="T",
            description="",
            modules=[
                ResolvedModule(
                    id="mod-01",
                    title="M",
                    description="",
                    locked=None,
                    assessments=[
                        ResolvedAssessment(
                            role="pre",
                            position="before_lessons",
                            source="quizazz",
                            ref="a/pre.yml",
                            pass_threshold=None,
                            content={"quizName": "pre"},
                        ),
                        ResolvedAssessment(
                            role="practice",
                            position={"before_lesson": "lesson-01"},
                            source="quizazz",
                            ref="a/practice.yml",
                            pass_threshold=0.7,
                            content={"quizName": "practice"},
                        ),
                        ResolvedAssessment(
                            role="post",
                            position="after_lessons",
                            source="quizazz",
                            ref="a/post.yml",
                            pass_threshold=0.8,
                            content={"quizName": "post"},
                        ),
                    ],
                    lessons=[
                        ResolvedLesson(id="lesson-01", title="L", content_blocks=[])
                    ],
                )
            ],
        )

    def test_assessments_emitted_in_order(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(
            self._make_with_assessments(), out, template_dir=TEMPLATE_DIR
        )
        data = json.loads((out / "static" / "curriculum.json").read_text())
        roles = [a["role"] for a in data["modules"][0]["assessments"]]
        assert roles == ["pre", "practice", "post"]

    def test_assessment_position_serialized_jsonable(
        self, tmp_path: Path
    ) -> None:
        out = tmp_path / "app"
        generate_app(
            self._make_with_assessments(), out, template_dir=TEMPLATE_DIR
        )
        data = json.loads((out / "static" / "curriculum.json").read_text())
        positions = [a["position"] for a in data["modules"][0]["assessments"]]
        assert positions == [
            "before_lessons",
            {"before_lesson": "lesson-01"},
            "after_lessons",
        ]

    def test_pass_threshold_passes_through(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(
            self._make_with_assessments(), out, template_dir=TEMPLATE_DIR
        )
        data = json.loads((out / "static" / "curriculum.json").read_text())
        thresholds = [a["pass_threshold"] for a in data["modules"][0]["assessments"]]
        assert thresholds == [None, 0.7, 0.8]

    def test_content_passes_through(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(
            self._make_with_assessments(), out, template_dir=TEMPLATE_DIR
        )
        data = json.loads((out / "static" / "curriculum.json").read_text())
        contents = [a["content"] for a in data["modules"][0]["assessments"]]
        assert contents == [
            {"quizName": "pre"},
            {"quizName": "practice"},
            {"quizName": "post"},
        ]

    def test_old_pre_post_fields_absent(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(_make_resolved(), out, template_dir=TEMPLATE_DIR)
        data = json.loads((out / "static" / "curriculum.json").read_text())
        mod = data["modules"][0]
        assert "pre_assessment" not in mod
        assert "post_assessment" not in mod
        assert mod["assessments"] == []


class TestTotalDurationMinutes:
    """Story J.c — `curriculum.total_duration_minutes` is the sum of
    `lesson.meta.duration_minutes` across the curriculum, or `null` when
    no lesson contributes."""

    def _make(
        self, *durations: int | None
    ) -> ResolvedCurriculum:
        """Build a curriculum with one module and one lesson per duration.

        ``None`` produces a lesson with no `meta`; an int produces a
        lesson whose `meta.duration_minutes` is set to that value.
        """
        lessons: list[ResolvedLesson] = []
        for i, d in enumerate(durations):
            meta: dict[str, object] | None
            meta = {"duration_minutes": d} if d is not None else None
            lessons.append(
                ResolvedLesson(
                    id=f"lesson-{i:02d}", title=f"L{i}", meta=meta, content_blocks=[]
                )
            )
        return ResolvedCurriculum(
            version="1.0.0",
            title="T",
            description="",
            modules=[
                ResolvedModule(
                    id="mod-01",
                    title="M",
                    description="",
                    locked=None,
                    lessons=lessons,
                )
            ],
        )

    def _read_total(self, out: Path) -> int | None:
        data = json.loads((out / "static" / "curriculum.json").read_text())
        return data["total_duration_minutes"]  # type: ignore[no-any-return]

    def test_aggregate_sums_all_contributors(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(self._make(15, 30, 45), out, template_dir=TEMPLATE_DIR)
        assert self._read_total(out) == 90

    def test_aggregate_skips_lessons_without_meta(self, tmp_path: Path) -> None:
        out = tmp_path / "app"
        generate_app(self._make(15, None, 30), out, template_dir=TEMPLATE_DIR)
        assert self._read_total(out) == 45

    def test_aggregate_is_null_when_no_lesson_contributes(
        self, tmp_path: Path
    ) -> None:
        out = tmp_path / "app"
        generate_app(self._make(None, None), out, template_dir=TEMPLATE_DIR)
        assert self._read_total(out) is None

    def test_aggregate_is_null_when_meta_present_but_no_duration(
        self, tmp_path: Path
    ) -> None:
        # `meta` set but `duration_minutes` absent should not poison the
        # aggregate (no contributors → null, not zero).
        out = tmp_path / "app"
        resolved = ResolvedCurriculum(
            version="1.0.0",
            title="T",
            description="",
            modules=[
                ResolvedModule(
                    id="mod-01",
                    title="M",
                    description="",
                    locked=None,
                    lessons=[
                        ResolvedLesson(
                            id="lesson-01",
                            title="L",
                            meta={"role": "opener"},
                            content_blocks=[],
                        )
                    ],
                )
            ],
        )
        generate_app(resolved, out, template_dir=TEMPLATE_DIR)
        assert self._read_total(out) is None


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
