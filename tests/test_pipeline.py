# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for the pipeline orchestrator."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from learningfoundry.exceptions import (
    ContentResolutionError,
    CurriculumValidationError,
)
from learningfoundry.generator import DepState
from learningfoundry.pipeline import run_build, run_preview, run_validate
from learningfoundry.resolver import ResolvedCurriculum

FIXTURES_DIR = Path(__file__).parent / "fixtures"
VALID_CURRICULUM = FIXTURES_DIR / "valid-curriculum.yml"


def _stub_providers() -> tuple[MagicMock, MagicMock, MagicMock]:
    quiz = MagicMock()
    quiz.compile_assessment.return_value = {"quizName": "q", "questions": []}
    exercise = MagicMock()
    exercise.compile_exercise.return_value = {"status": "stub"}
    vis = MagicMock()
    vis.compile_visualization.return_value = {"status": "stub"}
    return quiz, exercise, vis


class TestRunBuild:
    def test_returns_resolved_curriculum(self, tmp_path: Path) -> None:
        quiz, exercise, vis = _stub_providers()
        mock_gen = MagicMock()
        result = run_build(
            VALID_CURRICULUM,
            tmp_path / "out",
            base_dir=FIXTURES_DIR,
            quiz_provider=quiz,
            exercise_provider=exercise,
            visualization_provider=vis,
            generator=mock_gen,
        )
        assert isinstance(result, ResolvedCurriculum)

    def test_calls_generator_with_resolved_and_output_dir(
        self, tmp_path: Path
    ) -> None:
        quiz, exercise, vis = _stub_providers()
        mock_gen = MagicMock()
        out = tmp_path / "out"
        result = run_build(
            VALID_CURRICULUM,
            out,
            base_dir=FIXTURES_DIR,
            quiz_provider=quiz,
            exercise_provider=exercise,
            visualization_provider=vis,
            generator=mock_gen,
        )
        mock_gen.assert_called_once_with(result, out)

    def test_generator_receives_resolved_curriculum(self, tmp_path: Path) -> None:
        quiz, exercise, vis = _stub_providers()
        captured: list[ResolvedCurriculum] = []

        def capturing_gen(resolved: ResolvedCurriculum, output_dir: Path) -> None:
            captured.append(resolved)

        run_build(
            VALID_CURRICULUM,
            tmp_path / "out",
            base_dir=FIXTURES_DIR,
            quiz_provider=quiz,
            exercise_provider=exercise,
            visualization_provider=vis,
            generator=capturing_gen,
        )
        assert len(captured) == 1
        assert captured[0].version == "1.0.0"

    def test_defaults_base_dir_to_curriculum_parent(self, tmp_path: Path) -> None:
        quiz, exercise, vis = _stub_providers()
        mock_gen = MagicMock()
        # Copy fixture to tmp so base_dir can be inferred from parent
        import shutil
        import textwrap

        curriculum = tmp_path / "curriculum.yml"
        shutil.copy(VALID_CURRICULUM, curriculum)
        # Rewrite refs so they don't need real files (use no text blocks)
        curriculum.write_text(
            textwrap.dedent("""\
                version: "1.0.0"
                curriculum:
                  title: "T"
                  modules:
                    - id: mod-01
                      title: "M"
                      lessons:
                        - id: lesson-01
                          title: "L"
                          content_blocks: []
            """)
        )
        run_build(
            curriculum,
            tmp_path / "out",
            quiz_provider=quiz,
            exercise_provider=exercise,
            visualization_provider=vis,
            generator=mock_gen,
        )
        mock_gen.assert_called_once()

    def test_parse_error_propagates(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yml"
        bad.write_text("version: [unclosed\n")
        mock_gen = MagicMock()
        with pytest.raises(CurriculumValidationError):
            run_build(
                bad, tmp_path / "out", generator=mock_gen
            )
        mock_gen.assert_not_called()

    def test_resolve_error_propagates_without_generating(
        self, tmp_path: Path
    ) -> None:
        quiz = MagicMock()
        quiz.compile_assessment.side_effect = RuntimeError("boom")
        mock_gen = MagicMock()
        with pytest.raises((ContentResolutionError, Exception)):
            run_build(
                VALID_CURRICULUM,
                tmp_path / "out",
                base_dir=FIXTURES_DIR,
                quiz_provider=quiz,
                generator=mock_gen,
            )
        mock_gen.assert_not_called()


class TestRunValidate:
    def test_valid_curriculum_returns_true(self) -> None:
        quiz, exercise, vis = _stub_providers()
        is_valid, errors = run_validate(
            VALID_CURRICULUM,
            base_dir=FIXTURES_DIR,
            quiz_provider=quiz,
            exercise_provider=exercise,
            visualization_provider=vis,
        )
        assert is_valid is True
        assert errors == []

    def test_missing_file_returns_false(self, tmp_path: Path) -> None:
        is_valid, errors = run_validate(tmp_path / "nonexistent.yml")
        assert is_valid is False
        assert len(errors) == 1

    def test_invalid_curriculum_returns_errors(self, tmp_path: Path) -> None:
        bad = tmp_path / "curriculum.yml"
        bad.write_text("version: \"1.0.0\"\ncurriculum:\n  title: T\n  modules: []\n")
        is_valid, errors = run_validate(bad)
        assert is_valid is False
        assert len(errors) >= 1

    def test_validate_does_not_call_generator(self) -> None:
        quiz, exercise, vis = _stub_providers()
        with patch("learningfoundry.pipeline.run_build") as mock_build:
            run_validate(
                VALID_CURRICULUM,
                base_dir=FIXTURES_DIR,
                quiz_provider=quiz,
                exercise_provider=exercise,
                visualization_provider=vis,
            )
        mock_build.assert_not_called()

    def test_content_resolution_error_captured(self, tmp_path: Path) -> None:
        quiz = MagicMock()
        quiz.compile_assessment.side_effect = ContentResolutionError("bad ref")
        curriculum = tmp_path / "curriculum.yml"
        curriculum.write_text(
            "version: \"1.0.0\"\n"
            "curriculum:\n  title: T\n  modules:\n"
            "    - id: mod-01\n      title: M\n"
            "      pre_assessment:\n        source: quizazz\n"
            "        ref: assessments/pre.yml\n"
            "      lessons:\n        - id: lesson-01\n          title: L\n"
            "          content_blocks: []\n"
        )
        is_valid, errors = run_validate(
            curriculum,
            base_dir=tmp_path,
            quiz_provider=quiz,
        )
        assert is_valid is False
        assert any("bad ref" in e for e in errors)


class TestRunPreviewSkipsInstall:
    """``run_preview`` should skip the slow ``pnpm install`` step when every
    declared dependency is already present in ``node_modules/`` (i.e.
    ``check_dep_state`` returns ``UNCHANGED``). This is what makes the
    iterate-on-content loop fast: edit content → ``learningfoundry preview``
    → dev server starts immediately."""

    @staticmethod
    def _was_called_with_install(mock_run: MagicMock) -> bool:
        for call in mock_run.call_args_list:
            args = call.args[0] if call.args else call.kwargs.get("args", [])
            if isinstance(args, list) and args[:2] == ["pnpm", "install"]:
                return True
        return False

    def test_unchanged_state_skips_pnpm_install(self, tmp_path: Path) -> None:
        with (
            patch("learningfoundry.pipeline.run_build"),
            patch("learningfoundry.pipeline._ensure_sql_wasm"),
            patch(
                "learningfoundry.generator.check_dep_state",
                return_value=DepState.UNCHANGED,
            ),
            patch("learningfoundry.pipeline.subprocess.run") as mock_sub,
        ):
            mock_sub.return_value = MagicMock(returncode=0, stderr="")
            run_preview(VALID_CURRICULUM, tmp_path / "out", port=5174)
        assert not self._was_called_with_install(mock_sub), (
            "pnpm install should not have been invoked when DepState is UNCHANGED"
        )
        # `pnpm run dev` should still be called.
        assert any(
            (call.args[0] if call.args else []) == [
                "pnpm", "run", "dev", "--port", "5174"
            ]
            for call in mock_sub.call_args_list
        )

    def test_first_build_state_runs_pnpm_install(self, tmp_path: Path) -> None:
        with (
            patch("learningfoundry.pipeline.run_build"),
            patch("learningfoundry.pipeline._ensure_sql_wasm"),
            patch(
                "learningfoundry.generator.check_dep_state",
                return_value=DepState.FIRST_BUILD,
            ),
            patch("learningfoundry.pipeline.subprocess.run") as mock_sub,
        ):
            mock_sub.return_value = MagicMock(returncode=0, stderr="")
            run_preview(VALID_CURRICULUM, tmp_path / "out")
        assert self._was_called_with_install(mock_sub), (
            "pnpm install must run on FIRST_BUILD"
        )

    def test_changed_state_runs_pnpm_install(self, tmp_path: Path) -> None:
        with (
            patch("learningfoundry.pipeline.run_build"),
            patch("learningfoundry.pipeline._ensure_sql_wasm"),
            patch(
                "learningfoundry.generator.check_dep_state",
                return_value=DepState.CHANGED,
            ),
            patch("learningfoundry.pipeline.subprocess.run") as mock_sub,
        ):
            mock_sub.return_value = MagicMock(returncode=0, stderr="")
            run_preview(VALID_CURRICULUM, tmp_path / "out")
        assert self._was_called_with_install(mock_sub), (
            "pnpm install must run on CHANGED (new deps in package.json)"
        )


class TestRunPreviewProvisionsWasm:
    """`run_preview` must guarantee `static/sql-wasm.wasm` exists in the
    output directory before the dev server starts, regardless of whether
    `pnpm install` ran. Recording (lesson progress, quiz scores, exercise
    status) depends on the SvelteKit app fetching `/sql-wasm.wasm` to
    initialise sql.js — a 404 there silently breaks every DB write.

    The pre-fix pipeline relied on pnpm's `postinstall` hook to copy the
    file from `node_modules/sql.js/dist/sql-wasm.wasm`. That hook is
    skipped whenever `check_dep_state == UNCHANGED` (i.e. on every
    iterate-on-content rebuild), and is also unreliable across pnpm
    versions/configs that don't honour root-package lifecycle scripts.
    The Python pipeline is now the authority on this asset.
    """

    def _seed_node_modules_wasm(self, output_dir: Path) -> Path:
        """Create the `node_modules/sql.js/dist/sql-wasm.wasm` source the
        pipeline copies from. Returns the seeded path."""
        src = output_dir / "node_modules" / "sql.js" / "dist" / "sql-wasm.wasm"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_bytes(b"\x00asm-test-wasm-bytes")
        (output_dir / "static").mkdir(parents=True, exist_ok=True)
        return src

    def test_unchanged_state_still_provisions_wasm(self, tmp_path: Path) -> None:
        out = tmp_path / "out"
        out.mkdir()
        self._seed_node_modules_wasm(out)

        with (
            patch("learningfoundry.pipeline.run_build"),
            patch(
                "learningfoundry.generator.check_dep_state",
                return_value=DepState.UNCHANGED,
            ),
            patch("learningfoundry.pipeline.subprocess.run") as mock_sub,
        ):
            mock_sub.return_value = MagicMock(returncode=0, stderr="")
            run_preview(VALID_CURRICULUM, out)

        wasm = out / "static" / "sql-wasm.wasm"
        assert wasm.exists(), (
            "static/sql-wasm.wasm must be provisioned even when pnpm install "
            "is skipped — recording silently fails without it."
        )
        assert wasm.read_bytes() == b"\x00asm-test-wasm-bytes"

    def test_first_build_provisions_wasm_after_pnpm_install(
        self, tmp_path: Path
    ) -> None:
        out = tmp_path / "out"
        out.mkdir()
        seeded = self._seed_node_modules_wasm(out)

        with (
            patch("learningfoundry.pipeline.run_build"),
            patch(
                "learningfoundry.generator.check_dep_state",
                return_value=DepState.FIRST_BUILD,
            ),
            patch("learningfoundry.pipeline.subprocess.run") as mock_sub,
        ):
            mock_sub.return_value = MagicMock(returncode=0, stderr="")
            run_preview(VALID_CURRICULUM, out)

        wasm = out / "static" / "sql-wasm.wasm"
        assert wasm.exists()
        assert wasm.read_bytes() == seeded.read_bytes()

    def test_missing_wasm_source_raises_clear_error(self, tmp_path: Path) -> None:
        """If `node_modules/sql.js/dist/sql-wasm.wasm` is absent (e.g. pnpm
        install actually failed silently), the pipeline must fail loudly
        rather than start a dev server that will 404 on every DB init."""
        from learningfoundry.exceptions import GenerationError

        out = tmp_path / "out"
        (out / "static").mkdir(parents=True)
        # Note: no node_modules/sql.js/dist/sql-wasm.wasm seeded.

        with (
            patch("learningfoundry.pipeline.run_build"),
            patch(
                "learningfoundry.generator.check_dep_state",
                return_value=DepState.UNCHANGED,
            ),
            patch("learningfoundry.pipeline.subprocess.run") as mock_sub,
        ):
            mock_sub.return_value = MagicMock(returncode=0, stderr="")
            with pytest.raises(GenerationError, match="sql-wasm"):
                run_preview(VALID_CURRICULUM, out)
