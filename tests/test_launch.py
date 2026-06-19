# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for the marimo launch runtime (Story K.i)."""

import json
import signal
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
    launched_ports,
    marimo_argv,
    pidfile_path,
    port_holders,
    port_in_use,
    read_pidfile,
    reclaim_port,
    remove_pidfile,
    resolve_launch_spec,
    resolve_manifest_dir,
    spawn_detached,
    stop_launch_on_port,
    terminate_pid,
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


# ---------------------------------------------------------------------------
# spawn_detached
# ---------------------------------------------------------------------------


class TestSpawnDetached:
    def test_spawns_with_argv_cwd_and_new_session(self, tmp_path: Path) -> None:
        with patch("learningfoundry.launch.subprocess.Popen") as popen:
            popen.return_value.pid = 4242
            pid = spawn_detached(["marimo", "edit", "x.py"], tmp_path)
        assert pid == 4242
        args, kwargs = popen.call_args
        assert args[0] == ["marimo", "edit", "x.py"]
        assert kwargs["cwd"] == str(tmp_path)
        # Detached so marimo outlives the short-lived `launch` CLI process.
        assert kwargs.get("start_new_session") is True


# ---------------------------------------------------------------------------
# terminate_pid
# ---------------------------------------------------------------------------


class TestTerminatePid:
    def test_sigints_descendants_then_sigkills_whole_tree(self) -> None:
        # Kernels (descendants) get a graceful SIGINT to release semaphores;
        # then the whole tree (server + kernel) is force-killed.
        with (
            patch("learningfoundry.launch._descendants", return_value=[1001]),
            patch("learningfoundry.launch.os.kill") as kill,
            patch("learningfoundry.launch.time.sleep") as sleep,
        ):
            terminate_pid(4242, grace=2.0)
        kill.assert_any_call(1001, signal.SIGINT)  # graceful kernel teardown
        kill.assert_any_call(4242, signal.SIGKILL)  # force the server
        kill.assert_any_call(1001, signal.SIGKILL)  # force the kernel
        sleep.assert_called_once_with(2.0)  # the kernel-cleanup window

    def test_no_grace_sleep_when_no_descendants(self) -> None:
        with (
            patch("learningfoundry.launch._descendants", return_value=[]),
            patch("learningfoundry.launch.os.kill") as kill,
            patch("learningfoundry.launch.time.sleep") as sleep,
        ):
            terminate_pid(4242)
        sleep.assert_not_called()
        kill.assert_called_once_with(4242, signal.SIGKILL)

    def test_already_dead_is_noop(self) -> None:
        with (
            patch("learningfoundry.launch._descendants", return_value=[]),
            patch(
                "learningfoundry.launch.os.kill", side_effect=ProcessLookupError
            ),
        ):
            terminate_pid(4242)  # must not raise


class TestDescendants:
    def test_walks_the_ppid_tree(self) -> None:
        from learningfoundry.launch import _descendants

        # 200←100, 300←200 (grandchild), 400←1 (unrelated).
        fake_ps = "  100     1\n  200   100\n  300   200\n  400     1\n"
        with patch("learningfoundry.launch.subprocess.run") as run:
            run.return_value.stdout = fake_ps
            assert sorted(_descendants(100)) == [200, 300]


# ---------------------------------------------------------------------------
# port_holders / reclaim_port (Story K.l.2)
# ---------------------------------------------------------------------------


class TestPortHolders:
    def test_parses_lsof_pids(self) -> None:
        with patch("learningfoundry.launch.subprocess.run") as run:
            run.return_value.stdout = "9945\n11330\n"
            assert port_holders(2718) == [9945, 11330]

    def test_empty_when_nothing_holds_the_port(self) -> None:
        with patch("learningfoundry.launch.subprocess.run") as run:
            run.return_value.stdout = ""
            assert port_holders(2718) == []


class TestReclaimPort:
    def test_sigints_then_sigkills_holders_and_returns_them(self) -> None:
        with (
            patch("learningfoundry.launch.port_holders", return_value=[9945]),
            patch("learningfoundry.launch._descendants", return_value=[1001]),
            patch("learningfoundry.launch.os.kill") as kill,
            patch("learningfoundry.launch.time.sleep") as sleep,
        ):
            reclaimed = reclaim_port(2718, grace=2.0)
        assert reclaimed == [9945]
        # Holder + its descendant get a graceful SIGINT, then SIGKILL.
        kill.assert_any_call(9945, signal.SIGINT)
        kill.assert_any_call(1001, signal.SIGINT)
        kill.assert_any_call(9945, signal.SIGKILL)
        kill.assert_any_call(1001, signal.SIGKILL)
        sleep.assert_called_once_with(2.0)

    def test_noop_when_port_is_free(self) -> None:
        with (
            patch("learningfoundry.launch.port_holders", return_value=[]),
            patch("learningfoundry.launch.os.kill") as kill,
            patch("learningfoundry.launch.time.sleep") as sleep,
        ):
            assert reclaim_port(2718) == []
        kill.assert_not_called()
        sleep.assert_not_called()


# ---------------------------------------------------------------------------
# resolve_manifest_dir (Story K.l)
# ---------------------------------------------------------------------------


class TestResolveManifestDir:
    def _write_manifest(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "exercises-manifest.json").write_text("{}", encoding="utf-8")

    def test_returns_start_when_manifest_in_start(self, tmp_path: Path) -> None:
        self._write_manifest(tmp_path)
        assert resolve_manifest_dir(tmp_path) == tmp_path

    def test_falls_back_to_dist_subdir(self, tmp_path: Path) -> None:
        self._write_manifest(tmp_path / "dist")
        assert resolve_manifest_dir(tmp_path) == tmp_path / "dist"

    def test_prefers_start_over_dist(self, tmp_path: Path) -> None:
        self._write_manifest(tmp_path)
        self._write_manifest(tmp_path / "dist")
        assert resolve_manifest_dir(tmp_path) == tmp_path

    def test_returns_start_when_neither_exists(self, tmp_path: Path) -> None:
        # Falls through to `start` so ManifestNotFoundError fires with the
        # directory the user actually named.
        assert resolve_manifest_dir(tmp_path) == tmp_path


# ---------------------------------------------------------------------------
# stop_launch_on_port
# ---------------------------------------------------------------------------


class TestStopLaunchOnPort:
    def test_live_pidfile_terminates_removes_returns_entry(
        self, tmp_path: Path
    ) -> None:
        entry = PidfileEntry(
            pid=999, exercise_id="mnist-cnn", port=2718, mode="edit"
        )
        write_pidfile(tmp_path, entry)
        with (
            patch("learningfoundry.launch.pid_alive", return_value=True),
            patch("learningfoundry.launch.terminate_pid") as terminate,
        ):
            result = stop_launch_on_port(tmp_path, 2718)
        terminate.assert_called_once_with(999)
        assert result == entry
        assert not pidfile_path(tmp_path, 2718).exists()

    def test_stale_pidfile_removed_without_terminate(
        self, tmp_path: Path
    ) -> None:
        write_pidfile(
            tmp_path,
            PidfileEntry(pid=999, exercise_id="x", port=2718, mode="edit"),
        )
        with (
            patch("learningfoundry.launch.pid_alive", return_value=False),
            patch("learningfoundry.launch.terminate_pid") as terminate,
        ):
            result = stop_launch_on_port(tmp_path, 2718)
        terminate.assert_not_called()
        assert result is None
        assert not pidfile_path(tmp_path, 2718).exists()

    def test_absent_pidfile_is_noop(self, tmp_path: Path) -> None:
        with patch("learningfoundry.launch.terminate_pid") as terminate:
            assert stop_launch_on_port(tmp_path, 2718) is None
        terminate.assert_not_called()


# ---------------------------------------------------------------------------
# launched_ports
# ---------------------------------------------------------------------------


class TestLaunchedPorts:
    def test_lists_ports_from_pidfiles_sorted(self, tmp_path: Path) -> None:
        write_pidfile(
            tmp_path,
            PidfileEntry(pid=1, exercise_id="a", port=2719, mode="edit"),
        )
        write_pidfile(
            tmp_path,
            PidfileEntry(pid=2, exercise_id="b", port=2718, mode="run"),
        )
        assert launched_ports(tmp_path) == [2718, 2719]

    def test_empty_when_no_launch_dir(self, tmp_path: Path) -> None:
        assert launched_ports(tmp_path) == []
