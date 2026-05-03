# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""SvelteKit project generator — copies template and writes curriculum.json."""

import dataclasses
import json
import logging
import shutil
import tempfile
from enum import StrEnum
from pathlib import Path

from learningfoundry.exceptions import GenerationError
from learningfoundry.resolver import ResolvedCurriculum

logger = logging.getLogger("learningfoundry.generator")

_TEMPLATE_DIR = Path(__file__).parent / "sveltekit_template"

# Paths that represent install/build state in the generated project. These
# are preserved across `learningfoundry build` re-runs so the user does not
# have to `pnpm install` after every regen. Template files (package.json,
# src/, static/, configs) are still refreshed every time.
#
# `static/content` is preserved so previously-copied image assets
# (content-hashed under `static/content/<hash12>/<basename>`) survive a
# rebuild — keeps `learningfoundry preview` snappy when only markdown
# text changed and no new images were introduced.
#
# `static/sql-wasm.wasm` is preserved because it is gitignored and not
# shipped in the template — `pipeline._ensure_sql_wasm` is the single
# owner that provisions it from `node_modules/`. Preserving the file
# across rebuilds is belt-and-braces so a stale build never silently
# loses the asset between provisioning runs.
_PRESERVED_PATHS: tuple[str, ...] = (
    "node_modules",
    "pnpm-lock.yaml",
    "build",
    ".svelte-kit",
    "static/content",
    "static/sql-wasm.wasm",
)


class DepState(StrEnum):
    """State of installed dependencies relative to the generated package.json."""

    FIRST_BUILD = "first_build"
    """No `node_modules/` exists in the output directory."""

    UNCHANGED = "unchanged"
    """Every declared dep has a corresponding installed package."""

    CHANGED = "changed"
    """`node_modules/` exists but at least one declared dep is missing
    (e.g. user upgraded `learningfoundry` and the template added a new dep)."""


def generate_app(
    resolved: ResolvedCurriculum,
    output_dir: Path,
    template_dir: Path | None = None,
) -> None:
    """Generate a SvelteKit project from a resolved curriculum.

    Copies ``sveltekit_template/`` to ``output_dir`` atomically (write to a
    temp directory, then move into place), then writes ``curriculum.json``
    into ``output_dir/static/``.

    If ``output_dir`` already exists it is replaced with a warning.

    Args:
        resolved: Fully resolved curriculum from ``resolve_curriculum()``.
        output_dir: Destination path for the generated SvelteKit project.
        template_dir: Override template source. Defaults to the package's
            ``sveltekit_template/`` directory.

    Raises:
        GenerationError: If the template directory does not exist or any
            file operation fails.
    """
    src = template_dir or _TEMPLATE_DIR

    if not src.exists():
        raise GenerationError(
            f"SvelteKit template directory not found: `{src}`. "
            "Run `learningfoundry` from the project root, or pass "
            "`template_dir` explicitly."
        )

    if output_dir.exists():
        logger.info(
            "Output directory `%s` already exists; refreshing template files "
            "(preserving node_modules/, pnpm-lock.yaml, build/, .svelte-kit/).",
            output_dir,
        )

    _atomic_copy(src, output_dir)
    _copy_assets(resolved, output_dir)
    _write_curriculum_json(resolved, output_dir)

    logger.info("Generated SvelteKit project at: %s", output_dir)


def _atomic_copy(src: Path, dst: Path) -> None:
    """Copy src tree to dst atomically via a sibling temp directory.

    If ``dst`` already exists, install/build state listed in
    :data:`_PRESERVED_PATHS` is moved from the existing ``dst`` into the
    fresh template copy before the swap, so users do not have to re-run
    ``pnpm install`` after every ``learningfoundry build``.
    """
    parent = dst.parent
    parent.mkdir(parents=True, exist_ok=True)

    try:
        with tempfile.TemporaryDirectory(dir=parent, prefix=".lf_gen_") as tmp_str:
            tmp = Path(tmp_str) / dst.name
            # Never ship user-side artifacts from the template, even if a
            # local dev environment has them (e.g. a stray node_modules/
            # from running pnpm in the template dir during development).
            shutil.copytree(
                src,
                tmp,
                ignore=shutil.ignore_patterns(*_PRESERVED_PATHS),
            )
            if dst.exists():
                _move_preserved(dst, tmp)
                shutil.rmtree(dst)
            tmp.rename(dst)
    except OSError as exc:
        raise GenerationError(
            f"Failed to generate project at `{dst}`: {exc}"
        ) from exc


def _move_preserved(existing: Path, fresh: Path) -> None:
    """Move install/build state from ``existing`` into ``fresh`` in place.

    Any template-shipped placeholder at the same path inside ``fresh`` is
    removed first so the move never collides.
    """
    for name in _PRESERVED_PATHS:
        source = existing / name
        if not source.exists() and not source.is_symlink():
            continue
        target = fresh / name
        if target.exists() or target.is_symlink():
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(source), str(target))


def check_dep_state(output_dir: Path) -> DepState:
    """Inspect ``output_dir`` to determine whether `pnpm install` is needed.

    A dep is considered "installed" if ``node_modules/<name>/package.json``
    exists. We do not check version ranges — that is pnpm's job. This is a
    presence check designed to detect the common case where the generated
    `package.json` adds a new dep (e.g. after a `learningfoundry` upgrade)
    that is not yet in `node_modules/`.
    """
    node_modules = output_dir / "node_modules"
    if not node_modules.is_dir():
        return DepState.FIRST_BUILD

    package_json = output_dir / "package.json"
    if not package_json.is_file():
        return DepState.FIRST_BUILD

    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # Malformed package.json — surface as "changed" so the user is
        # nudged to run pnpm install (which will report the real error).
        return DepState.CHANGED

    declared: dict[str, str] = {
        **(data.get("dependencies") or {}),
        **(data.get("devDependencies") or {}),
    }
    for name in declared:
        if not (node_modules / name / "package.json").is_file():
            return DepState.CHANGED
    return DepState.UNCHANGED


def _write_curriculum_json(resolved: ResolvedCurriculum, output_dir: Path) -> None:
    """Serialize ResolvedCurriculum to output_dir/static/curriculum.json.

    The ``assets`` list is intentionally stripped — it carries on-disk
    ``Path`` objects (which are not JSON-serialisable) and is consumed only
    by the generator's asset-copy step, never by the SvelteKit frontend.
    """
    static_dir = output_dir / "static"
    static_dir.mkdir(parents=True, exist_ok=True)

    curriculum_json = output_dir / "static" / "curriculum.json"
    try:
        data = dataclasses.asdict(resolved)
        data.pop("assets", None)
        curriculum_json.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise GenerationError(
            f"Failed to write curriculum.json to `{curriculum_json}`: {exc}"
        ) from exc

    logger.debug("Wrote curriculum.json (%d bytes)", curriculum_json.stat().st_size)


def _copy_assets(resolved: ResolvedCurriculum, output_dir: Path) -> None:
    """Copy each ``Asset`` to ``output_dir/static/<dest_relative>``.

    Idempotent: a destination file whose size matches the source is left
    untouched. Because ``dest_relative`` is content-hashed
    (``content/<sha256[:12]>/<basename>``), a matching size on a path with a
    matching hash implies matching content — re-copying would be wasted I/O.
    """
    if not resolved.assets:
        return

    static_dir = output_dir / "static"
    static_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped = 0
    for asset in resolved.assets:
        dest = static_dir / asset.dest_relative
        try:
            if dest.is_file() and dest.stat().st_size == asset.source.stat().st_size:
                skipped += 1
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(asset.source, dest)
            copied += 1
        except OSError as exc:
            raise GenerationError(
                f"Failed to copy image asset `{asset.source}` "
                f"to `{dest}`: {exc}"
            ) from exc

    logger.info(
        "Copied %d image asset(s) into static/ (%d already up to date).",
        copied,
        skipped,
    )
