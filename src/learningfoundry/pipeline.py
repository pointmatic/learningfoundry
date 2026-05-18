# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Pipeline orchestrator — parse → resolve → generate."""

import logging
import shutil
import subprocess
import tomllib
from collections.abc import Callable
from pathlib import Path

from learningfoundry.integrations.protocols import (
    ExerciseProvider,
    QuizProvider,
    VisualizationProvider,
)
from learningfoundry.parser import parse_curriculum
from learningfoundry.resolver import ResolvedCurriculum, resolve_curriculum
from learningfoundry.schema_extensions import (
    build_extended_curriculum_v1,
    load_schema_extensions,
)
from learningfoundry.schema_v1 import CurriculumV1

logger = logging.getLogger("learningfoundry.pipeline")

GeneratorFn = Callable[[ResolvedCurriculum, Path], None]

SCHEMA_EXTENSIONS_FILENAME = "learningfoundry-schema-extensions.yml"


def resolve_schema_extensions_path(
    cli_path: Path | None,
    curriculum_path: Path,
) -> Path | None:
    """Resolve the schema-extensions file path using the documented
    precedence: CLI flag > ``pyproject.toml`` setting > auto-discovery
    next to the curriculum > none.

    Returns ``None`` when no source provides a path — callers should
    treat this as "use base meta models unchanged".
    """
    if cli_path is not None:
        return cli_path

    curriculum_dir = curriculum_path.parent
    pyproject = curriculum_dir / "pyproject.toml"
    if pyproject.is_file():
        try:
            with pyproject.open("rb") as f:
                data = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError):
            data = {}
        ext_setting = (
            data.get("tool", {}).get("learningfoundry", {}).get("schema_extensions")
        )
        if isinstance(ext_setting, str) and ext_setting:
            return (curriculum_dir / ext_setting).resolve()

    auto = curriculum_dir / SCHEMA_EXTENSIONS_FILENAME
    if auto.is_file():
        return auto

    return None


def _build_extended_model_cls(
    schema_extensions_path: Path | None,
    curriculum_path: Path,
) -> type[CurriculumV1] | None:
    """Resolve + load the schema-extensions file (if any) and synthesize
    the extended ``CurriculumV1`` subclass. Returns ``None`` when no
    extensions are in effect — caller should use the base dispatch."""
    ext_path = resolve_schema_extensions_path(
        schema_extensions_path, curriculum_path
    )
    if ext_path is None:
        return None
    logger.info("Loading schema extensions from: %s", ext_path)
    extensions = load_schema_extensions(ext_path)
    return build_extended_curriculum_v1(extensions)


def run_build(
    curriculum_path: Path,
    output_dir: Path,
    base_dir: Path | None = None,
    schema_extensions_path: Path | None = None,
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

    extended_model_cls = _build_extended_model_cls(
        schema_extensions_path, curriculum_path
    )

    logger.info("Parsing curriculum: %s", curriculum_path)
    curriculum = parse_curriculum(curriculum_path, model_cls=extended_model_cls)

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
    schema_extensions_path: Path | None = None,
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
        extended_model_cls = _build_extended_model_cls(
            schema_extensions_path, curriculum_path
        )
        logger.info("Validating curriculum: %s", curriculum_path)
        curriculum = parse_curriculum(curriculum_path, model_cls=extended_model_cls)
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
    schema_extensions_path: Path | None = None,
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
        schema_extensions_path=schema_extensions_path,
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
