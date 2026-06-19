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
import time
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


def resolve_manifest_dir(start: Path) -> Path:
    """Locate the directory that holds ``exercises-manifest.json``.

    The learner typically runs ``launch``/``stop`` from the curriculum project
    root, where ``build`` writes the app into ``dist/`` — so the manifest is at
    ``dist/exercises-manifest.json``, not in the cwd. Prefer ``start`` itself
    (running from inside the app), then fall back to ``start/dist``. If neither
    holds the manifest, return ``start`` unchanged so the downstream
    :class:`ManifestNotFoundError` names the directory the user actually gave.
    """
    if (start / MANIFEST_FILENAME).is_file():
        return start
    nested = start / "dist"
    if (nested / MANIFEST_FILENAME).is_file():
        return nested
    return start


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


def _signal(pid: int, sig: int) -> None:
    """`os.kill` that swallows "already gone"."""
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        pass


def _descendants(pid: int) -> list[int]:
    """All transitive child pids of ``pid`` (POSIX, via ``ps``).

    Walks the ppid tree rather than the process *group* so it finds marimo's
    notebook kernel even though marimo isolates it in its own process group —
    the kernel is still a child here.
    """
    try:
        out = subprocess.run(
            ["ps", "-Ao", "pid=,ppid="],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
    except OSError:  # pragma: no cover - ps should always exist on POSIX
        return []
    children: dict[int, list[int]] = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            children.setdefault(int(parts[1]), []).append(int(parts[0]))
    result: list[int] = []
    stack = [pid]
    while stack:
        for child in children.get(stack.pop(), []):
            if child not in result:
                result.append(child)
                stack.append(child)
    return result


def terminate_pid(pid: int, *, grace: float = 2.0) -> None:
    """Stop the launch-owned marimo at ``pid`` and all its descendants —
    promptly and without the late goodbye / leaked-semaphore noise.

    marimo isolates each notebook **kernel** in its own process group with a
    parent-poller, so a signal sent to the server's process group never reaches
    the kernel: orphaned, it notices the dead server only on its next poll and
    shuts down *late*, leaking its multiprocessing semaphores (the hang this
    fixes). Empirically the marimo **server** ignores ``SIGINT`` and lingers
    several seconds on ``SIGTERM``, so no graceful signal stops it promptly.

    Strategy: walk the ppid tree (which reaches the kernel despite its separate
    group), ``SIGINT`` the descendants — the kernel handles SIGINT and releases
    its semaphores — give them a brief ``grace`` window to do so, then
    ``SIGKILL`` the whole tree. Force-killing the tree (rather than waiting on
    the slow server) keeps ``stop`` snappy and kills the ``resource_tracker``
    before it can emit a late leaked-semaphore warning. Windows uses
    ``taskkill /T`` (tree). An already-exited process is treated as success.
    """
    if sys.platform == "win32":  # pragma: no cover - Windows only
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            check=False,
            capture_output=True,
        )
        return

    kids = _descendants(pid)
    for child in kids:
        _signal(child, signal.SIGINT)  # graceful kernel teardown
    if kids:
        time.sleep(grace)  # let kernels release their semaphores
    for p in [pid, *_descendants(pid)]:
        _signal(p, signal.SIGKILL)  # force the tree down — prompt and quiet


def port_holders(port: int) -> list[int]:
    """Pids holding ``port`` (POSIX, via ``lsof -ti``).

    Used by ``--force`` reclaim to find an abandoned marimo whose own pidfile
    pid is dead — e.g. an orphaned kernel that outlived its server and still
    holds the inherited listening-socket fd. Empty if ``lsof`` is unavailable.
    """
    try:
        out = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
    except OSError:  # pragma: no cover - lsof missing (e.g. Windows)
        return []
    return [int(tok) for tok in out.split() if tok.isdigit()]


def reclaim_port(port: int, *, grace: float = 2.0) -> list[int]:
    """Force-free ``port`` by tearing down whatever holds it; return those pids.

    Used by ``learningfoundry launch --force``. Like :func:`terminate_pid` it
    ``SIGINT``s the holders **and their descendants** first (so an orphaned
    marimo kernel releases its semaphores), waits a brief window, then
    ``SIGKILL``s the set. Never invoked without the caller's explicit
    ``--force`` opt-in — the default policy is to refuse a foreign port.
    """
    holders = port_holders(port)
    if not holders:
        return []
    targets: set[int] = set(holders)
    for holder in holders:
        targets.update(_descendants(holder))
    for p in targets:
        _signal(p, signal.SIGINT)
    time.sleep(grace)
    final: set[int] = set(holders)
    for holder in holders:
        final.update(_descendants(holder))
    for p in final:
        _signal(p, signal.SIGKILL)
    return holders


def stop_launch_on_port(manifest_dir: Path, port: int) -> PidfileEntry | None:
    """Stop the launch-owned marimo recorded for ``port``, if any.

    Returns the stopped :class:`PidfileEntry`, or ``None`` if nothing
    launch-owned was running (no pidfile, or a stale one whose process is
    already gone — which is cleaned up either way). A port with no pidfile is a
    *foreign* process and is never touched. Shared by ``launch``'s replace path
    and the ``stop`` command.
    """
    entry = read_pidfile(manifest_dir, port)
    if entry is None:
        return None
    if pid_alive(entry.pid):
        terminate_pid(entry.pid)
        remove_pidfile(manifest_dir, port)
        return entry
    # Stale pidfile — the process already exited; just clean up.
    remove_pidfile(manifest_dir, port)
    return None


def launched_ports(manifest_dir: Path) -> list[int]:
    """Return the ports of all launch pidfiles under ``manifest_dir``, sorted.

    Empty if ``.learningfoundry/`` does not exist. Filenames that do not parse
    as ``launch-<int>.pid`` are skipped.
    """
    ports: list[int] = []
    for path in (manifest_dir / _PIDFILE_DIR).glob("launch-*.pid"):
        try:
            ports.append(int(path.stem.removeprefix("launch-")))
        except ValueError:
            continue
    return sorted(ports)
