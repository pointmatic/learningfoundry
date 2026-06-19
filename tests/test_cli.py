# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for the CLI build and validate commands."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from learningfoundry.cli import (
    EXIT_CONFIG,
    EXIT_RESOLUTION,
    EXIT_RUNTIME,
    EXIT_VALIDATION,
    main,
)
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


# ---------------------------------------------------------------------------
# launch (Story K.i.3)
# ---------------------------------------------------------------------------


def _write_launch_manifest(tmp_path: Path) -> None:
    manifest = {
        "mnist-cnn": {
            "notebook_path": "exercises/mnist-cnn/mnist-cnn.py",
            "mode": "edit",
            "port": 2718,
        }
    }
    (tmp_path / "exercises-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )


_EXPECTED_ARGV = [
    "marimo",
    "edit",
    "exercises/mnist-cnn/mnist-cnn.py",
    "--headless",
    "-p",
    "2718",
    "--no-token",
]


class TestLaunch:
    def test_free_port_spawns_marimo_and_writes_pidfile(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        _write_launch_manifest(tmp_path)
        with (
            patch(
                "learningfoundry.cli.shutil.which",
                return_value="/usr/local/bin/marimo",
            ),
            patch(
                "learningfoundry.launch.classify_port", return_value="free"
            ),
            patch("learningfoundry.launch.subprocess.Popen") as popen,
        ):
            popen.return_value.pid = 12345
            result = runner.invoke(
                main, ["launch", "mnist-cnn", "--dir", str(tmp_path)]
            )

        assert result.exit_code == 0, result.output
        args, kwargs = popen.call_args
        assert args[0] == _EXPECTED_ARGV
        assert kwargs["cwd"] == str(tmp_path)

        pidfile = tmp_path / ".learningfoundry" / "launch-2718.pid"
        assert pidfile.exists()
        data = json.loads(pidfile.read_text())
        assert data["pid"] == 12345
        assert data["exercise_id"] == "mnist-cnn"
        assert "localhost:2718" in result.output

    def test_foreign_port_refuses_and_does_not_spawn(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        _write_launch_manifest(tmp_path)
        with (
            patch(
                "learningfoundry.cli.shutil.which",
                return_value="/usr/local/bin/marimo",
            ),
            patch(
                "learningfoundry.launch.classify_port", return_value="foreign"
            ),
            patch("learningfoundry.launch.subprocess.Popen") as popen,
        ):
            result = runner.invoke(
                main, ["launch", "mnist-cnn", "--dir", str(tmp_path)]
            )

        assert result.exit_code == EXIT_RUNTIME
        popen.assert_not_called()

    def test_ours_replace_confirmed_kills_old_and_spawns(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        _write_launch_manifest(tmp_path)
        pidfile = tmp_path / ".learningfoundry" / "launch-2718.pid"
        pidfile.parent.mkdir(parents=True)
        pidfile.write_text(
            json.dumps(
                {
                    "pid": 999,
                    "exercise_id": "mnist-cnn",
                    "port": 2718,
                    "mode": "edit",
                }
            ),
            encoding="utf-8",
        )
        with (
            patch(
                "learningfoundry.cli.shutil.which",
                return_value="/usr/local/bin/marimo",
            ),
            patch(
                "learningfoundry.launch.classify_port", return_value="ours"
            ),
            # An `ours` port has a live pid; the shared stop helper checks it.
            patch("learningfoundry.launch.pid_alive", return_value=True),
            patch("learningfoundry.launch.terminate_pid") as terminate,
            patch("learningfoundry.launch.subprocess.Popen") as popen,
        ):
            popen.return_value.pid = 12345
            result = runner.invoke(
                main,
                ["launch", "mnist-cnn", "--dir", str(tmp_path)],
                input="y\n",
            )

        assert result.exit_code == 0, result.output
        terminate.assert_called_once_with(999)
        popen.assert_called_once()
        assert json.loads(pidfile.read_text())["pid"] == 12345

    def test_ours_replace_declined_aborts(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        _write_launch_manifest(tmp_path)
        pidfile = tmp_path / ".learningfoundry" / "launch-2718.pid"
        pidfile.parent.mkdir(parents=True)
        pidfile.write_text(
            json.dumps(
                {
                    "pid": 999,
                    "exercise_id": "mnist-cnn",
                    "port": 2718,
                    "mode": "edit",
                }
            ),
            encoding="utf-8",
        )
        with (
            patch(
                "learningfoundry.cli.shutil.which",
                return_value="/usr/local/bin/marimo",
            ),
            patch(
                "learningfoundry.launch.classify_port", return_value="ours"
            ),
            patch("learningfoundry.launch.subprocess.Popen") as popen,
        ):
            result = runner.invoke(
                main,
                ["launch", "mnist-cnn", "--dir", str(tmp_path)],
                input="n\n",
            )

        assert result.exit_code == 0
        popen.assert_not_called()
        # The running exercise's pidfile is left untouched.
        assert json.loads(pidfile.read_text())["pid"] == 999

    def test_marimo_not_installed_errors_with_hint(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        _write_launch_manifest(tmp_path)
        with (
            patch("learningfoundry.cli.shutil.which", return_value=None),
            patch("learningfoundry.launch.subprocess.Popen") as popen,
        ):
            result = runner.invoke(
                main, ["launch", "mnist-cnn", "--dir", str(tmp_path)]
            )

        assert result.exit_code == EXIT_RUNTIME
        assert "marimo" in result.output.lower()
        popen.assert_not_called()

    def test_unknown_exercise_id_exits_validation(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        _write_launch_manifest(tmp_path)
        result = runner.invoke(
            main, ["launch", "nope", "--dir", str(tmp_path)]
        )
        assert result.exit_code == EXIT_VALIDATION
        assert "nope" in result.output
        assert "mnist-cnn" in result.output


# ---------------------------------------------------------------------------
# stop (Story K.i.4)
# ---------------------------------------------------------------------------


def _write_pidfile(tmp_path: Path, port: int, pid: int, exercise_id: str) -> Path:
    path = tmp_path / ".learningfoundry" / f"launch-{port}.pid"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "pid": pid,
                "exercise_id": exercise_id,
                "port": port,
                "mode": "edit",
            }
        ),
        encoding="utf-8",
    )
    return path


class TestStop:
    def test_stop_by_id_terminates_and_removes_pidfile(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        _write_launch_manifest(tmp_path)
        pidfile = _write_pidfile(tmp_path, 2718, 999, "mnist-cnn")
        with (
            patch("learningfoundry.launch.pid_alive", return_value=True),
            patch("learningfoundry.launch.terminate_pid") as terminate,
        ):
            result = runner.invoke(
                main, ["stop", "mnist-cnn", "--dir", str(tmp_path)]
            )
        assert result.exit_code == 0, result.output
        terminate.assert_called_once_with(999)
        assert not pidfile.exists()
        assert "mnist-cnn" in result.output

    def test_stop_all_iterates_every_pidfile(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        _write_launch_manifest(tmp_path)
        pf1 = _write_pidfile(tmp_path, 2718, 999, "mnist-cnn")
        pf2 = _write_pidfile(tmp_path, 2719, 888, "linreg")
        with (
            patch("learningfoundry.launch.pid_alive", return_value=True),
            patch("learningfoundry.launch.terminate_pid") as terminate,
        ):
            result = runner.invoke(main, ["stop", "--dir", str(tmp_path)])
        assert result.exit_code == 0, result.output
        killed = {call.args[0] for call in terminate.call_args_list}
        assert killed == {999, 888}
        assert not pf1.exists()
        assert not pf2.exists()

    def test_stop_by_id_with_no_pidfile_is_noop_success(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        _write_launch_manifest(tmp_path)
        with patch("learningfoundry.launch.terminate_pid") as terminate:
            result = runner.invoke(
                main, ["stop", "mnist-cnn", "--dir", str(tmp_path)]
            )
        # No launch-owned process for this port → nothing killed, exit 0.
        assert result.exit_code == 0
        terminate.assert_not_called()

    def test_stop_all_with_no_pidfiles_touches_nothing(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        _write_launch_manifest(tmp_path)
        with patch("learningfoundry.launch.terminate_pid") as terminate:
            result = runner.invoke(main, ["stop", "--dir", str(tmp_path)])
        assert result.exit_code == 0
        # A foreign process holding a port has no pidfile, so it is never
        # touched — stop acts solely through launch-owned pidfiles.
        terminate.assert_not_called()


# ---------------------------------------------------------------------------
# launch/stop auto-detect dist/ (Story K.l) — learner runs from project root
# ---------------------------------------------------------------------------


class TestLaunchStopAutoDetectDist:
    def test_launch_finds_manifest_under_dist(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        # Manifest lives in dist/, not the cwd the learner runs from.
        dist = tmp_path / "dist"
        dist.mkdir()
        _write_launch_manifest(dist)
        with (
            patch(
                "learningfoundry.cli.shutil.which",
                return_value="/usr/local/bin/marimo",
            ),
            patch("learningfoundry.launch.classify_port", return_value="free"),
            patch("learningfoundry.launch.subprocess.Popen") as popen,
        ):
            popen.return_value.pid = 12345
            result = runner.invoke(
                main, ["launch", "mnist-cnn", "--dir", str(tmp_path)]
            )
        assert result.exit_code == 0, result.output
        # Pidfile written under dist/, proving the auto-detect resolved there.
        assert (dist / ".learningfoundry" / "launch-2718.pid").exists()
        assert not (tmp_path / ".learningfoundry").exists()

    def test_stop_finds_manifest_under_dist(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        dist = tmp_path / "dist"
        dist.mkdir()
        _write_launch_manifest(dist)
        pidfile = _write_pidfile(dist, 2718, 999, "mnist-cnn")
        with (
            patch("learningfoundry.launch.pid_alive", return_value=True),
            patch("learningfoundry.launch.terminate_pid") as terminate,
        ):
            result = runner.invoke(
                main, ["stop", "mnist-cnn", "--dir", str(tmp_path)]
            )
        assert result.exit_code == 0, result.output
        terminate.assert_called_once_with(999)
        assert not pidfile.exists()
