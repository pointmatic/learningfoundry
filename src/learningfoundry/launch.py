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
import os
import signal
import socket
import subprocess
import sys
from dataclasses import asdict, dataclass
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


# ---------------------------------------------------------------------------
# Runtime primitives (K.i.2) — port probe, pidfile, liveness, ownership
# ---------------------------------------------------------------------------

# Pidfiles for launch-owned marimo processes live under this dir, keyed by port
# (the contended resource). One file per running notebook.
_PIDFILE_DIR = ".learningfoundry"

PortStatus = Literal["free", "ours", "foreign"]


def port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Return ``True`` if something is accepting connections on ``host:port``.

    A short-timeout connect probe — a successful connection means the port is
    held; a refused/timed-out connection means it is free.
    """
    try:
        with socket.create_connection((host, port), timeout=0.25):
            return True
    except OSError:
        return False


@dataclass(frozen=True)
class PidfileEntry:
    """The contents of a launch pidfile — enough to know what is running on a
    port and that *we* started it (so ``stop`` never kills a foreign process)."""

    pid: int
    exercise_id: str
    port: int
    mode: Mode


def pidfile_path(manifest_dir: Path, port: int) -> Path:
    """Path of the pidfile for ``port`` under ``manifest_dir/.learningfoundry``."""
    return manifest_dir / _PIDFILE_DIR / f"launch-{port}.pid"


def write_pidfile(manifest_dir: Path, entry: PidfileEntry) -> Path:
    """Write ``entry`` as JSON, creating ``.learningfoundry/`` if needed.

    Returns the pidfile path.
    """
    path = pidfile_path(manifest_dir, entry.port)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(entry), indent=2) + "\n", encoding="utf-8"
    )
    return path


def read_pidfile(manifest_dir: Path, port: int) -> PidfileEntry | None:
    """Read the pidfile for ``port``, or ``None`` if it is absent or corrupt.

    A corrupt/partial pidfile is treated as absent rather than raising — a
    stale file must never crash ``launch``/``stop``.
    """
    path = pidfile_path(manifest_dir, port)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    try:
        data = json.loads(raw)
        return PidfileEntry(
            pid=int(data["pid"]),
            exercise_id=str(data["exercise_id"]),
            port=int(data["port"]),
            mode=data["mode"],
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def remove_pidfile(manifest_dir: Path, port: int) -> None:
    """Delete the pidfile for ``port`` if present (idempotent)."""
    pidfile_path(manifest_dir, port).unlink(missing_ok=True)


def pid_alive(pid: int) -> bool:
    """Return ``True`` if a process with ``pid`` currently exists.

    POSIX uses signal-0 (``os.kill(pid, 0)``); Windows uses ``OpenProcess`` via
    ``ctypes``. The Windows branch is smoke-only (CI is POSIX).
    """
    if os.name == "nt":  # pragma: no cover - exercised only on Windows
        return _pid_alive_windows(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # The process exists but is owned by another user — still "alive".
        return True
    return True


def _pid_alive_windows(pid: int) -> bool:  # pragma: no cover - Windows only
    import ctypes

    process_query_limited_information = 0x1000
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    handle = kernel32.OpenProcess(
        process_query_limited_information, False, pid
    )
    if not handle:
        return False
    kernel32.CloseHandle(handle)
    return True


def classify_port(manifest_dir: Path, port: int) -> PortStatus:
    """Classify ``port`` as ``free``, ``ours``, or ``foreign``.

    - ``ours``    — a live launch-owned pidfile points at this port.
    - ``foreign`` — the port is held but no live launch pidfile owns it
                    (some other process; never blind-killed).
    - ``free``    — nothing is listening and no live pidfile owns it.

    A pidfile whose process is dead is *stale*; it is deleted here so the port
    reclassifies cleanly on the next read.
    """
    entry = read_pidfile(manifest_dir, port)
    if entry is not None and pid_alive(entry.pid):
        return "ours"
    if entry is not None:
        # Stale pidfile — its process is gone; clean it up before probing.
        remove_pidfile(manifest_dir, port)
    return "foreign" if port_in_use(port) else "free"


# ---------------------------------------------------------------------------
# Process lifecycle (K.i.3) — spawn / terminate
# ---------------------------------------------------------------------------


def spawn_detached(argv: list[str], cwd: Path) -> int:
    """Spawn ``argv`` as a detached background process; return its pid.

    Detached so the marimo server outlives the short-lived ``launch`` CLI
    process — the learner gets their shell back immediately. ``cwd`` is the
    launch directory so the notebook's relative path (and any data/assets it
    reads) resolve from the app root.
    """
    if sys.platform == "win32":  # pragma: no cover - Windows only
        proc = subprocess.Popen(
            argv,
            cwd=str(cwd),
            creationflags=(
                subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
                | subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
            ),
            close_fds=True,
        )
    else:
        proc = subprocess.Popen(argv, cwd=str(cwd), start_new_session=True)
    return proc.pid


def terminate_pid(pid: int) -> None:
    """Ask the process ``pid`` to terminate (idempotent if already gone).

    POSIX sends ``SIGTERM`` (graceful); Windows shells out to ``taskkill``.
    A process that has already exited is treated as success.
    """
    if sys.platform == "win32":  # pragma: no cover - Windows only
        subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)],
            check=False,
            capture_output=True,
        )
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass  # already gone — nothing to do
