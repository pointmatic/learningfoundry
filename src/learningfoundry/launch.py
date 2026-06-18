# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Learner-side marimo launch runtime (Story K.i).

A static SvelteKit app cannot spawn or kill an OS process, so the lifecycle of
an exercise's marimo notebook lives in this CLI that the *learner* runs:
``learningfoundry launch <id>`` resolves the notebook + port from the
``exercises-manifest.json`` sidecar that ``build`` emits, then spawns
``marimo edit|run … --headless``.

This module (K.i.1) is the pure core — manifest resolution and argv
construction. Sockets, pidfiles, and process spawning live in later stories of
the bundle (K.i.2–K.i.4).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from learningfoundry.exceptions import (
    ManifestError,
    ManifestNotFoundError,
    UnknownExerciseError,
)

Mode = Literal["edit", "run"]

# Sidecar written by the generator at the project root (see generator.py
# ``_write_exercises``). The learner runs ``launch``/``stop`` from inside the
# generated app, where this file lives.
MANIFEST_FILENAME = "exercises-manifest.json"

# Required keys in each manifest entry, mirroring the generator's manifest shape
# (``id -> {notebook_path, mode, port}``).
_REQUIRED_FIELDS = ("notebook_path", "mode", "port")


@dataclass(frozen=True)
class LaunchSpec:
    """The resolved "what to launch" for a single exercise.

    ``notebook_path`` is relative to the launch directory (the manifest's
    location); ``mode`` selects ``marimo edit`` vs ``marimo run``; ``port`` is
    where the local marimo server binds.
    """

    id: str
    notebook_path: str
    mode: Mode
    port: int


def resolve_launch_spec(manifest_dir: Path, exercise_id: str) -> LaunchSpec:
    """Resolve an exercise id to its :class:`LaunchSpec` from the manifest.

    Reads ``manifest_dir/exercises-manifest.json``. Raises
    :class:`ManifestNotFoundError` if the sidecar is absent,
    :class:`ManifestError` if it is malformed, and
    :class:`UnknownExerciseError` (listing the available ids) if ``exercise_id``
    is not present.
    """
    manifest_path = manifest_dir / MANIFEST_FILENAME
    try:
        raw = manifest_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ManifestNotFoundError(
            f"No `{MANIFEST_FILENAME}` found in `{manifest_dir}`. Run "
            "`learningfoundry launch`/`stop` from the generated app's root "
            "(or pass --dir), and make sure the app has been built."
        ) from exc

    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ManifestError(
            f"`{manifest_path}` is not valid JSON: {exc}"
        ) from exc

    if not isinstance(manifest, dict):
        raise ManifestError(
            f"`{manifest_path}` must be a JSON object mapping exercise ids to "
            f"entries, got {type(manifest).__name__}."
        )

    if exercise_id not in manifest:
        available = ", ".join(sorted(manifest)) or "(none)"
        raise UnknownExerciseError(
            f"Unknown exercise id `{exercise_id}`. "
            f"Available exercises: {available}."
        )

    entry = manifest[exercise_id]
    if not isinstance(entry, dict) or any(
        field not in entry for field in _REQUIRED_FIELDS
    ):
        raise ManifestError(
            f"Manifest entry for `{exercise_id}` in `{manifest_path}` is "
            f"malformed; expected an object with {_REQUIRED_FIELDS}, "
            f"got {entry!r}."
        )

    return LaunchSpec(
        id=exercise_id,
        notebook_path=str(entry["notebook_path"]),
        mode=entry["mode"],
        port=int(entry["port"]),
    )


def marimo_argv(spec: LaunchSpec) -> list[str]:
    """Build the marimo command for ``spec``.

    ``marimo edit|run <path> --headless -p <port> --no-token`` — ``--headless``
    so it does not try to open a browser from the CLI process, ``--no-token``
    because the banner links straight to the local URL.
    """
    return [
        "marimo",
        spec.mode,
        spec.notebook_path,
        "--headless",
        "-p",
        str(spec.port),
        "--no-token",
    ]
