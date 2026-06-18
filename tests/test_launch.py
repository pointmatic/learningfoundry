# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for the marimo launch runtime (Story K.i)."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from learningfoundry.exceptions import (
    ManifestError,
    ManifestNotFoundError,
    UnknownExerciseError,
)
from learningfoundry.launch import (
    LaunchSpec,
    PidfileEntry,
    classify_port,
    marimo_argv,
    pidfile_path,
    port_in_use,
    read_pidfile,
    remove_pidfile,
    resolve_launch_spec,
    write_pidfile,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_manifest(manifest_dir: Path, data: object) -> Path:
    path = manifest_dir / "exercises-manifest.json"
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_text(json.dumps(data), encoding="utf-8")
    return path


_VALID_MANIFEST = {
    "mnist-cnn": {
        "notebook_path": "exercises/mnist-cnn/mnist-cnn.py",
        "mode": "edit",
        "port": 2718,
    },
    "linreg": {
        "notebook_path": "exercises/linreg/linreg.py",
        "mode": "run",
        "port": 2718,
    },
}


# ---------------------------------------------------------------------------
# resolve_launch_spec
# ---------------------------------------------------------------------------


class TestResolveLaunchSpec:
    def test_resolves_edit_exercise(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, _VALID_MANIFEST)
        spec = resolve_launch_spec(tmp_path, "mnist-cnn")
        assert spec == LaunchSpec(
            id="mnist-cnn",
            notebook_path="exercises/mnist-cnn/mnist-cnn.py",
            mode="edit",
            port=2718,
        )

    def test_resolves_run_exercise(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, _VALID_MANIFEST)
        spec = resolve_launch_spec(tmp_path, "linreg")
        assert spec.mode == "run"
        assert spec.notebook_path == "exercises/linreg/linreg.py"

    def test_missing_manifest_raises_manifest_not_found(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(ManifestNotFoundError) as exc:
            resolve_launch_spec(tmp_path, "mnist-cnn")
        assert "exercises-manifest.json" in str(exc.value)

    def test_unknown_id_lists_available_ids(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, _VALID_MANIFEST)
        with pytest.raises(UnknownExerciseError) as exc:
            resolve_launch_spec(tmp_path, "nope")
        message = str(exc.value)
        assert "nope" in message
        # The error must list the ids the learner can actually launch.
        assert "mnist-cnn" in message
        assert "linreg" in message

    def test_malformed_json_raises_manifest_error(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, "{ this is not json")
        with pytest.raises(ManifestError):
            resolve_launch_spec(tmp_path, "mnist-cnn")

    def test_manifest_not_an_object_raises_manifest_error(
        self, tmp_path: Path
    ) -> None:
        _write_manifest(tmp_path, ["not", "a", "mapping"])
        with pytest.raises(ManifestError):
            resolve_launch_spec(tmp_path, "mnist-cnn")

    def test_entry_missing_field_raises_manifest_error(
        self, tmp_path: Path
    ) -> None:
        _write_manifest(tmp_path, {"mnist-cnn": {"mode": "edit", "port": 2718}})
        with pytest.raises(ManifestError):
            resolve_launch_spec(tmp_path, "mnist-cnn")


# ---------------------------------------------------------------------------
# marimo_argv
# ---------------------------------------------------------------------------


class TestMarimoArgv:
    def test_edit_mode_argv(self) -> None:
        spec = LaunchSpec(
            id="mnist-cnn",
            notebook_path="exercises/mnist-cnn/mnist-cnn.py",
            mode="edit",
            port=2718,
        )
        assert marimo_argv(spec) == [
            "marimo",
            "edit",
            "exercises/mnist-cnn/mnist-cnn.py",
            "--headless",
            "-p",
            "2718",
            "--no-token",
        ]

    def test_run_mode_argv(self) -> None:
        spec = LaunchSpec(
            id="linreg",
            notebook_path="exercises/linreg/linreg.py",
            mode="run",
            port=2718,
        )
        argv = marimo_argv(spec)
        assert argv[:3] == ["marimo", "run", "exercises/linreg/linreg.py"]
        assert "--headless" in argv
        assert "--no-token" in argv
        assert argv[argv.index("-p") + 1] == "2718"


# ---------------------------------------------------------------------------
# port_in_use
# ---------------------------------------------------------------------------


class TestPortInUse:
    def test_returns_true_when_connection_succeeds(self) -> None:
        with patch("learningfoundry.launch.socket.create_connection"):
            assert port_in_use(2718) is True

    def test_returns_false_when_connection_refused(self) -> None:
        with patch(
            "learningfoundry.launch.socket.create_connection",
            side_effect=OSError("refused"),
        ):
            assert port_in_use(2718) is False


# ---------------------------------------------------------------------------
# pidfile layer
# ---------------------------------------------------------------------------


class TestPidfile:
    def test_pidfile_path_layout(self, tmp_path: Path) -> None:
        path = pidfile_path(tmp_path, 2718)
        assert path == tmp_path / ".learningfoundry" / "launch-2718.pid"
        assert path.parent.name == ".learningfoundry"

    def test_write_then_read_round_trips(self, tmp_path: Path) -> None:
        entry = PidfileEntry(
            pid=4321, exercise_id="mnist-cnn", port=2718, mode="edit"
        )
        written = write_pidfile(tmp_path, entry)
        assert written == pidfile_path(tmp_path, 2718)
        assert written.exists()
        assert read_pidfile(tmp_path, 2718) == entry

    def test_write_creates_parent_dir(self, tmp_path: Path) -> None:
        entry = PidfileEntry(
            pid=1, exercise_id="x", port=2718, mode="run"
        )
        assert not (tmp_path / ".learningfoundry").exists()
        write_pidfile(tmp_path, entry)
        assert (tmp_path / ".learningfoundry").is_dir()

    def test_read_missing_returns_none(self, tmp_path: Path) -> None:
        assert read_pidfile(tmp_path, 2718) is None

    def test_read_malformed_returns_none(self, tmp_path: Path) -> None:
        path = pidfile_path(tmp_path, 2718)
        path.parent.mkdir(parents=True)
        path.write_text("{ not json", encoding="utf-8")
        assert read_pidfile(tmp_path, 2718) is None

    def test_remove_is_idempotent(self, tmp_path: Path) -> None:
        # Removing an absent pidfile is a no-op, not an error.
        remove_pidfile(tmp_path, 2718)
        write_pidfile(
            tmp_path,
            PidfileEntry(pid=1, exercise_id="x", port=2718, mode="edit"),
        )
        remove_pidfile(tmp_path, 2718)
        assert not pidfile_path(tmp_path, 2718).exists()


# ---------------------------------------------------------------------------
# classify_port
# ---------------------------------------------------------------------------


class TestClassifyPort:
    def test_ours_when_pidfile_alive(self, tmp_path: Path) -> None:
        write_pidfile(
            tmp_path,
            PidfileEntry(pid=999, exercise_id="x", port=2718, mode="edit"),
        )
        with patch("learningfoundry.launch.pid_alive", return_value=True):
            assert classify_port(tmp_path, 2718) == "ours"

    def test_foreign_when_no_pidfile_but_port_busy(self, tmp_path: Path) -> None:
        with patch("learningfoundry.launch.port_in_use", return_value=True):
            assert classify_port(tmp_path, 2718) == "foreign"

    def test_free_when_no_pidfile_and_port_idle(self, tmp_path: Path) -> None:
        with patch("learningfoundry.launch.port_in_use", return_value=False):
            assert classify_port(tmp_path, 2718) == "free"

    def test_stale_pidfile_is_removed_and_reclassified(
        self, tmp_path: Path
    ) -> None:
        # Pidfile present but its process is dead and the port is now idle:
        # the stale file is cleaned up and the port reads as free.
        write_pidfile(
            tmp_path,
            PidfileEntry(pid=999, exercise_id="x", port=2718, mode="edit"),
        )
        with (
            patch("learningfoundry.launch.pid_alive", return_value=False),
            patch("learningfoundry.launch.port_in_use", return_value=False),
        ):
            assert classify_port(tmp_path, 2718) == "free"
        assert not pidfile_path(tmp_path, 2718).exists()
