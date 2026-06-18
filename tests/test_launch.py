# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for the marimo launch runtime (Story K.i)."""

import json
from pathlib import Path

import pytest

from learningfoundry.exceptions import (
    ManifestError,
    ManifestNotFoundError,
    UnknownExerciseError,
)
from learningfoundry.launch import LaunchSpec, marimo_argv, resolve_launch_spec

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
