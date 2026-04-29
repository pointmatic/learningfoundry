# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for the CLI build and validate commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from learningfoundry.cli import EXIT_CONFIG, EXIT_RESOLUTION, EXIT_VALIDATION, main
from learningfoundry.exceptions import (
    ContentResolutionError,
    CurriculumValidationError,
    GenerationError,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
VALID_CURRICULUM = FIXTURES_DIR / "valid-curriculum.yml"


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# --help / --version
# ---------------------------------------------------------------------------


class TestHelpAndVersion:
    def test_main_help_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "build" in result.output
        assert "validate" in result.output

    def test_build_help_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["build", "--help"])
        assert result.exit_code == 0
        assert "--config" in result.output
        assert "--output" in result.output

    def test_validate_help_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["validate", "--help"])
        assert result.exit_code == 0
        assert "--config" in result.output

    def test_version_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "learningfoundry" in result.output


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------


class TestBuildCommand:
    def test_build_success_exits_zero(self, runner: CliRunner, tmp_path: Path) -> None:
        with patch("learningfoundry.pipeline.run_build") as mock_run:
            mock_run.return_value = MagicMock()
            result = runner.invoke(
                main,
                [
                    "build",
                    "--config", str(VALID_CURRICULUM),
                    "--output", str(tmp_path / "out"),
                    "--base-dir", str(FIXTURES_DIR),
                ],
            )
        assert result.exit_code == 0
        assert "Build complete" in result.output

    def test_build_prints_output_path(self, runner: CliRunner, tmp_path: Path) -> None:
        out = tmp_path / "myapp"
        with patch("learningfoundry.pipeline.run_build"):
            result = runner.invoke(
                main,
                ["build", "--config", str(VALID_CURRICULUM), "--output", str(out)],
            )
        assert str(out) in result.output

    def test_build_validation_error_exits_1(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        with patch(
            "learningfoundry.pipeline.run_build",
            side_effect=CurriculumValidationError("bad schema"),
        ):
            result = runner.invoke(
                main,
                ["build", "--config", str(VALID_CURRICULUM), "--output", str(tmp_path)],
            )
        assert result.exit_code == EXIT_VALIDATION
        assert "Validation error" in result.output

    def test_build_resolution_error_exits_2(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        with patch(
            "learningfoundry.pipeline.run_build",
            side_effect=ContentResolutionError("missing file"),
        ):
            result = runner.invoke(
                main,
                ["build", "--config", str(VALID_CURRICULUM), "--output", str(tmp_path)],
            )
        assert result.exit_code == EXIT_RESOLUTION
        assert "resolution error" in result.output

    def test_build_generation_error_exits_3(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        with patch(
            "learningfoundry.pipeline.run_build",
            side_effect=GenerationError("template missing"),
        ):
            result = runner.invoke(
                main,
                ["build", "--config", str(VALID_CURRICULUM), "--output", str(tmp_path)],
            )
        assert result.exit_code == 3

    def test_build_missing_config_file(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        result = runner.invoke(
            main,
            ["build", "--config", str(tmp_path / "nonexistent.yml")],
        )
        assert result.exit_code != 0


class TestBuildNextStepsPrompt:
    """The post-build prompt is the user's primary signpost to the next
    command. It must consistently recommend `learningfoundry preview` (the
    canonical iterate-on-content path) for every `DepState`, and surface a
    distinct warning when dependencies have changed since the last install."""

    def _invoke(
        self, runner: CliRunner, tmp_path: Path, state: object
    ) -> str:
        from learningfoundry.generator import DepState

        assert isinstance(state, DepState)
        with (
            patch("learningfoundry.pipeline.run_build"),
            patch(
                "learningfoundry.generator.check_dep_state", return_value=state
            ),
        ):
            result = runner.invoke(
                main,
                [
                    "build",
                    "--config", str(VALID_CURRICULUM),
                    "--output", str(tmp_path / "out"),
                ],
            )
        assert result.exit_code == 0
        return result.output

    def test_first_build_recommends_preview(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        from learningfoundry.generator import DepState

        out = self._invoke(runner, tmp_path, DepState.FIRST_BUILD)
        assert "Next: learningfoundry preview" in out
        assert "static export to deploy" in out
        assert "Dependencies changed" not in out

    def test_unchanged_recommends_preview(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        from learningfoundry.generator import DepState

        out = self._invoke(runner, tmp_path, DepState.UNCHANGED)
        assert "Next: learningfoundry preview" in out
        assert "static export to deploy" in out
        assert "Dependencies changed" not in out

    def test_changed_warns_then_recommends_preview(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        from learningfoundry.generator import DepState

        out = self._invoke(runner, tmp_path, DepState.CHANGED)
        assert "Dependencies changed" in out
        assert "learningfoundry preview" in out
        assert "will reinstall" in out


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


class TestValidateCommand:
    def test_validate_valid_curriculum_exits_zero(
        self, runner: CliRunner
    ) -> None:
        with patch(
            "learningfoundry.pipeline.run_validate", return_value=(True, [])
        ):
            result = runner.invoke(
                main,
                ["validate", "--config", str(VALID_CURRICULUM)],
            )
        assert result.exit_code == 0
        assert "OK" in result.output

    def test_validate_invalid_curriculum_exits_1(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        bad = tmp_path / "bad.yml"
        bad.write_text("version: \"1.0.0\"\ncurriculum:\n  title: T\n  modules: []\n")
        result = runner.invoke(main, ["validate", "--config", str(bad)])
        assert result.exit_code == EXIT_VALIDATION

    def test_validate_reports_errors(
        self, runner: CliRunner
    ) -> None:
        with patch(
            "learningfoundry.pipeline.run_validate",
            return_value=(False, ["mod-01: missing file"]),
        ):
            result = runner.invoke(
                main,
                ["validate", "--config", str(VALID_CURRICULUM)],
            )
        assert result.exit_code == EXIT_VALIDATION
        assert "mod-01" in result.output

    def test_validate_missing_config_exits_nonzero(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        result = runner.invoke(
            main,
            ["validate", "--config", str(tmp_path / "nonexistent.yml")],
        )
        assert result.exit_code != 0

    def test_validate_exit_config_on_config_error(
        self, runner: CliRunner
    ) -> None:
        from learningfoundry.exceptions import ConfigError

        with patch(
            "learningfoundry.pipeline.run_validate",
            side_effect=ConfigError("bad config"),
        ):
            result = runner.invoke(
                main,
                ["validate", "--config", str(VALID_CURRICULUM)],
            )
        assert result.exit_code == EXIT_CONFIG


# ---------------------------------------------------------------------------
# preview
# ---------------------------------------------------------------------------


class TestPreviewCommand:
    def test_preview_help_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["preview", "--help"])
        assert result.exit_code == 0
        assert "--port" in result.output
        assert "--config" in result.output

    def test_preview_calls_run_preview(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        with patch("learningfoundry.pipeline.run_preview") as mock_preview:
            runner.invoke(
                main,
                [
                    "preview",
                    "--config", str(VALID_CURRICULUM),
                    "--output", str(tmp_path / "out"),
                    "--port", "5174",
                ],
            )
        mock_preview.assert_called_once()
        _, kwargs = mock_preview.call_args
        assert kwargs.get("port") == 5174 or mock_preview.call_args.args[2] == 5174

    def test_preview_prints_url(self, runner: CliRunner, tmp_path: Path) -> None:
        with patch("learningfoundry.pipeline.run_preview"):
            result = runner.invoke(
                main,
                [
                    "preview",
                    "--config", str(VALID_CURRICULUM),
                    "--output", str(tmp_path / "out"),
                    "--port", "5200",
                ],
            )
        assert "5200" in result.output
        assert "localhost" in result.output

    def test_preview_default_port_is_5173(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        with patch("learningfoundry.pipeline.run_preview") as mock_preview:
            runner.invoke(
                main,
                [
                    "preview",
                    "--config", str(VALID_CURRICULUM),
                    "--output", str(tmp_path / "out"),
                ],
            )
        call_kwargs = mock_preview.call_args
        # port is positional arg index 2 or keyword
        args, kwargs = call_kwargs
        port = kwargs.get("port", args[2] if len(args) > 2 else None)
        assert port == 5173

    def test_preview_validation_error_exits_1(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        with patch(
            "learningfoundry.pipeline.run_preview",
            side_effect=CurriculumValidationError("bad"),
        ):
            result = runner.invoke(
                main,
                ["preview", "--config", str(VALID_CURRICULUM)],
            )
        assert result.exit_code == EXIT_VALIDATION

    def test_preview_generation_error_exits_3(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        with patch(
            "learningfoundry.pipeline.run_preview",
            side_effect=GenerationError("pnpm missing"),
        ):
            result = runner.invoke(
                main,
                ["preview", "--config", str(VALID_CURRICULUM)],
            )
        assert result.exit_code == 3
