# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Pipeline orchestrator — parse → resolve → generate."""

import logging
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from learningfoundry.integrations.protocols import (
    ExerciseProvider,
    QuizProvider,
    VisualizationProvider,
)
from learningfoundry.parser import parse_curriculum
from learningfoundry.resolver import ResolvedCurriculum, resolve_curriculum

logger = logging.getLogger("learningfoundry.pipeline")

GeneratorFn = Callable[[ResolvedCurriculum, Path], None]


def run_build(
    curriculum_path: Path,
    output_dir: Path,
    base_dir: Path | None = None,
    quiz_provider: QuizProvider | None = None,
    exercise_provider: ExerciseProvider | None = None,
    visualization_provider: VisualizationProvider | None = None,
    generator: GeneratorFn | None = None,
) -> ResolvedCurriculum:
    """Parse → resolve → generate in one call.

    Args:
        curriculum_path: Path to the curriculum YAML file.
        output_dir: Destination directory for the generated SvelteKit project.
        base_dir: Root for resolving content refs. Defaults to the directory
            containing ``curriculum_path``.
        quiz_provider: Override for quiz resolution. Defaults to
            ``QuizazzProvider``.
        exercise_provider: Override for exercise resolution. Defaults to
            ``NbfoundryStub``.
        visualization_provider: Override for visualization resolution. Defaults
            to ``D3foundryStub``.
        generator: Override for the SvelteKit generator callable. Defaults to
            ``learningfoundry.generator.generate_app``.

    Returns:
        The fully resolved ``ResolvedCurriculum`` (after generation).

    Raises:
        CurriculumVersionError: Unsupported or missing curriculum version.
        CurriculumValidationError: Schema validation failure.
        ContentResolutionError: Any content reference that cannot be resolved.
        GenerationError: SvelteKit project generation failure.
    """
    resolved_base = base_dir or curriculum_path.parent

    logger.info("Parsing curriculum: %s", curriculum_path)
    curriculum = parse_curriculum(curriculum_path)

    logger.info("Resolving content references (base_dir=%s)", resolved_base)
    resolved = resolve_curriculum(
        curriculum,
        resolved_base,
        quiz_provider=quiz_provider,
        exercise_provider=exercise_provider,
        visualization_provider=visualization_provider,
    )

    if generator is None:
        from learningfoundry.generator import generate_app

        generator = generate_app

    logger.info("Generating SvelteKit project at: %s", output_dir)
    generator(resolved, output_dir)

    logger.info("Build complete: %s", output_dir)
    return resolved


def run_validate(
    curriculum_path: Path,
    base_dir: Path | None = None,
    quiz_provider: QuizProvider | None = None,
    exercise_provider: ExerciseProvider | None = None,
    visualization_provider: VisualizationProvider | None = None,
) -> tuple[bool, list[str]]:
    """Parse and resolve without generating — validation only.

    Args:
        curriculum_path: Path to the curriculum YAML file.
        base_dir: Root for resolving content refs.
        quiz_provider: Override for quiz resolution.
        exercise_provider: Override for exercise resolution.
        visualization_provider: Override for visualization resolution.

    Returns:
        Tuple of ``(is_valid, errors)`` where ``errors`` is empty on success
        and contains human-readable error strings on failure.
    """
    resolved_base = base_dir or curriculum_path.parent
    errors: list[str] = []

    try:
        logger.info("Validating curriculum: %s", curriculum_path)
        curriculum = parse_curriculum(curriculum_path)
        resolve_curriculum(
            curriculum,
            resolved_base,
            quiz_provider=quiz_provider,
            exercise_provider=exercise_provider,
            visualization_provider=visualization_provider,
        )
        logger.info("Validation passed.")
    except Exception as exc:
        errors.append(str(exc))
        logger.error("Validation failed: %s", exc)

    return (len(errors) == 0, errors)


def run_preview(
    curriculum_path: Path,
    output_dir: Path,
    port: int = 5173,
    base_dir: Path | None = None,
    quiz_provider: QuizProvider | None = None,
    exercise_provider: ExerciseProvider | None = None,
    visualization_provider: VisualizationProvider | None = None,
    generator: GeneratorFn | None = None,
) -> None:
    """Build then launch a local preview server.

    Runs ``run_build()``, then ``pnpm install`` (only when needed) and
    ``pnpm run dev --port`` in the generated project directory. The install
    step is skipped when ``check_dep_state(output_dir)`` reports
    ``DepState.UNCHANGED`` — i.e. every dependency declared in the
    generated ``package.json`` is already present in ``node_modules/``.

    Args:
        curriculum_path: Path to the curriculum YAML file.
        output_dir: Destination directory for the generated SvelteKit project.
        port: Dev server port. Defaults to 5173.
        base_dir: Root for resolving content refs.
        quiz_provider: Override for quiz resolution.
        exercise_provider: Override for exercise resolution.
        visualization_provider: Override for visualization resolution.
        generator: Override for the SvelteKit generator callable.

    Raises:
        GenerationError: If build or pnpm commands fail.
    """
    from learningfoundry.exceptions import GenerationError
    from learningfoundry.generator import DepState, check_dep_state

    run_build(
        curriculum_path,
        output_dir,
        base_dir=base_dir,
        quiz_provider=quiz_provider,
        exercise_provider=exercise_provider,
        visualization_provider=visualization_provider,
        generator=generator,
    )

    state = check_dep_state(output_dir)
    if state is DepState.UNCHANGED:
        logger.info("Dependencies up to date — skipping pnpm install.")
    else:
        logger.info("Installing Node dependencies in %s", output_dir)
        result = subprocess.run(
            ["pnpm", "install"],
            cwd=output_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise GenerationError(
                f"`pnpm install` failed in `{output_dir}`:\n{result.stderr}"
            )

    _ensure_sql_wasm(output_dir)

    logger.info("Starting dev server on port %d", port)
    subprocess.run(
        ["pnpm", "run", "dev", "--port", str(port)],
        cwd=output_dir,
    )


def _ensure_sql_wasm(output_dir: Path) -> None:
    """Provision ``static/sql-wasm.wasm`` from the installed sql.js package.

    sql.js is loaded in the browser via ``initSqlJs({ locateFile: () =>
    '/sql-wasm.wasm' })`` (see ``src/lib/db/database.ts``). If that URL
    404s, every progress / quiz / exercise write silently fails — the
    "recording is broken after second preview" bug.

    This step is the single owner of the asset. It runs every preview
    (regardless of ``DepState``) and copies the wasm out of
    ``node_modules/sql.js/dist/`` into ``static/`` whenever the
    destination is missing or content-stale. Replaces the previous
    pnpm ``postinstall`` hook, which only ran on actual installs and
    was unreliable across pnpm version/configuration combinations.

    Raises:
        GenerationError: If the source wasm in ``node_modules/`` is
            missing — better to fail the build loudly than start a dev
            server that 404s on every DB init.
    """
    from learningfoundry.exceptions import GenerationError

    src = output_dir / "node_modules" / "sql.js" / "dist" / "sql-wasm.wasm"
    dst = output_dir / "static" / "sql-wasm.wasm"

    if not src.is_file():
        raise GenerationError(
            f"sql-wasm.wasm source not found at `{src}`. "
            "`pnpm install` likely failed silently or sql.js is not in "
            "the generated `package.json`. The dev server cannot serve "
            "/sql-wasm.wasm without this file and recording will not work."
        )

    if dst.is_file() and dst.stat().st_size == src.stat().st_size:
        # Cheap content check — sql.js wasm is content-addressed by
        # version-pinned dep in package.json, so size match is a strong
        # proxy for "same bytes" without reading both files.
        return

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    logger.info(
        "Provisioned static/sql-wasm.wasm from node_modules/sql.js (%d bytes)",
        dst.stat().st_size,
    )
