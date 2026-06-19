# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0

import shutil
import sys
from pathlib import Path

import click

from learningfoundry import __version__
from learningfoundry.exceptions import (
    ConfigError,
    ContentResolutionError,
    CurriculumValidationError,
    CurriculumVersionError,
    GenerationError,
    LaunchError,
    SchemaExtensionError,
)
from learningfoundry.logging_config import setup_logging as _setup_logging

# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------
EXIT_VALIDATION = 1
EXIT_RESOLUTION = 2
EXIT_GENERATION = 3
EXIT_CONFIG = 4
EXIT_RUNTIME = 5


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(version=__version__, prog_name="learningfoundry")
def main() -> None:
    """A curriculum engine that generates deployable SvelteKit learning apps."""


# ---------------------------------------------------------------------------
# Shared options
# ---------------------------------------------------------------------------

_config_option = click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default="curriculum.yml",
    show_default=True,
    help="Path to the curriculum YAML file.",
)

_log_level_option = click.option(
    "--log-level",
    "log_level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    show_default=True,
    help="Logging verbosity.",
)

_schema_extensions_option = click.option(
    "--schema-extensions",
    "schema_extensions_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help=(
        "Path to a project-specific schema-extensions YAML file. "
        "Resolution order: this flag > [tool.learningfoundry] "
        "schema_extensions in pyproject.toml > auto-discovery of "
        "`learningfoundry-schema-extensions.yml` next to the curriculum > none."
    ),
)


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

@main.command()
@_config_option
@_log_level_option
@_schema_extensions_option
@click.option(
    "--output",
    "-o",
    "output_dir",
    type=click.Path(path_type=Path),
    default="dist",
    show_default=True,
    help="Output directory for the generated SvelteKit project.",
)
@click.option(
    "--base-dir",
    "base_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Base directory for content refs (default: curriculum file's parent dir).",
)
def build(
    config_path: Path,
    log_level: str,
    schema_extensions_path: Path | None,
    output_dir: Path,
    base_dir: Path | None,
) -> None:
    """Parse → resolve → generate a SvelteKit project."""
    _setup_logging(level=log_level)

    from learningfoundry.pipeline import run_build

    try:
        run_build(
            config_path,
            output_dir,
            base_dir=base_dir,
            schema_extensions_path=schema_extensions_path,
        )
    except (CurriculumValidationError, CurriculumVersionError) as exc:
        click.echo(f"Validation error: {exc}", err=True)
        sys.exit(EXIT_VALIDATION)
    except ContentResolutionError as exc:
        click.echo(f"Content resolution error: {exc}", err=True)
        sys.exit(EXIT_RESOLUTION)
    except GenerationError as exc:
        click.echo(f"Generation error: {exc}", err=True)
        sys.exit(EXIT_GENERATION)
    except SchemaExtensionError as exc:
        click.echo(f"Schema-extensions error: {exc}", err=True)
        sys.exit(EXIT_CONFIG)
    except ConfigError as exc:
        click.echo(f"Config error: {exc}", err=True)
        sys.exit(EXIT_CONFIG)

    click.echo(f"Build complete → {output_dir}")

    from learningfoundry.generator import DepState, check_dep_state

    state = check_dep_state(output_dir)
    click.echo("")
    if state is DepState.CHANGED:
        click.echo(
            "⚠️  Dependencies changed since last install "
            "(new packages in package.json) — `learningfoundry preview` "
            "will reinstall."
        )
    click.echo("Next: learningfoundry preview")
    click.echo(
        f"  (or `cd {output_dir} && pnpm build` for a static export to deploy)"
    )


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@main.command()
@_config_option
@_log_level_option
@_schema_extensions_option
@click.option(
    "--base-dir",
    "base_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Base directory for resolving content refs.",
)
def validate(
    config_path: Path,
    log_level: str,
    schema_extensions_path: Path | None,
    base_dir: Path | None,
) -> None:
    """Validate a curriculum YAML without generating output."""
    _setup_logging(level=log_level)

    from learningfoundry.pipeline import run_validate

    try:
        is_valid, errors = run_validate(
            config_path,
            base_dir=base_dir,
            schema_extensions_path=schema_extensions_path,
        )
    except SchemaExtensionError as exc:
        click.echo(f"Schema-extensions error: {exc}", err=True)
        sys.exit(EXIT_CONFIG)
    except ConfigError as exc:
        click.echo(f"Config error: {exc}", err=True)
        sys.exit(EXIT_CONFIG)

    if is_valid:
        click.echo("OK — curriculum is valid.")
    else:
        for err in errors:
            click.echo(f"  ✗ {err}", err=True)
        click.echo(f"Validation failed ({len(errors)} error(s)).", err=True)
        sys.exit(EXIT_VALIDATION)


# ---------------------------------------------------------------------------
# preview
# ---------------------------------------------------------------------------

@main.command()
@_config_option
@_log_level_option
@_schema_extensions_option
@click.option(
    "--output",
    "-o",
    "output_dir",
    type=click.Path(path_type=Path),
    default="dist",
    show_default=True,
    help="Output directory for the generated SvelteKit project.",
)
@click.option(
    "--base-dir",
    "base_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Base directory for content refs (default: curriculum file's parent dir).",
)
@click.option(
    "--port",
    "port",
    type=int,
    default=5173,
    show_default=True,
    help="Port for the local dev server.",
)
def preview(
    config_path: Path,
    log_level: str,
    schema_extensions_path: Path | None,
    output_dir: Path,
    base_dir: Path | None,
    port: int,
) -> None:
    """Build then launch a local preview server."""
    _setup_logging(level=log_level)

    from learningfoundry.pipeline import run_preview

    click.echo(f"Building → {output_dir} …")

    try:
        run_preview(
            config_path,
            output_dir,
            port=port,
            base_dir=base_dir,
            schema_extensions_path=schema_extensions_path,
        )
    except (CurriculumValidationError, CurriculumVersionError) as exc:
        click.echo(f"Validation error: {exc}", err=True)
        sys.exit(EXIT_VALIDATION)
    except ContentResolutionError as exc:
        click.echo(f"Content resolution error: {exc}", err=True)
        sys.exit(EXIT_RESOLUTION)
    except GenerationError as exc:
        click.echo(f"Generation error: {exc}", err=True)
        sys.exit(EXIT_GENERATION)
    except SchemaExtensionError as exc:
        click.echo(f"Schema-extensions error: {exc}", err=True)
        sys.exit(EXIT_CONFIG)
    except ConfigError as exc:
        click.echo(f"Config error: {exc}", err=True)
        sys.exit(EXIT_CONFIG)

    click.echo(f"Preview server started at http://localhost:{port}")


# ---------------------------------------------------------------------------
# launch
# ---------------------------------------------------------------------------

_launch_dir_option = click.option(
    "--dir",
    "launch_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
    help=(
        "Where to find `exercises-manifest.json`. Auto-detects "
        "`<dir>/exercises-manifest.json`, else `<dir>/dist/...`. "
        "Defaults to the current directory."
    ),
)


@main.command()
@click.argument("exercise_id")
@_launch_dir_option
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help=(
        "Reclaim the port if it is held by another process (terminates it), "
        "and replace a running exercise without prompting."
    ),
)
@_log_level_option
def launch(
    exercise_id: str, launch_dir: Path, force: bool, log_level: str
) -> None:
    """Launch an exercise's marimo notebook locally."""
    _setup_logging(level=log_level)

    from learningfoundry import launch as _launch

    launch_dir = _launch.resolve_manifest_dir(launch_dir)

    try:
        spec = _launch.resolve_launch_spec(launch_dir, exercise_id)
    except LaunchError as exc:
        click.echo(f"Launch error: {exc}", err=True)
        sys.exit(EXIT_VALIDATION)

    if shutil.which("marimo") is None:
        click.echo(
            "marimo not found on PATH. It is a learner-runtime dependency — "
            "install it (e.g. `pip install marimo`) to run exercises.",
            err=True,
        )
        sys.exit(EXIT_RUNTIME)

    status = _launch.classify_port(launch_dir, spec.port)
    if status == "foreign":
        if not force:
            click.echo(
                f"Port {spec.port} is in use by another process. Refusing to "
                "kill it — free the port (or pass --force to reclaim it) and "
                "retry.",
                err=True,
            )
            sys.exit(EXIT_RUNTIME)
        reclaimed = _launch.reclaim_port(spec.port)
        pids = ", ".join(str(p) for p in reclaimed) or "none"
        click.echo(f"Reclaimed port {spec.port} (stopped pid(s): {pids}).")
    if status == "ours":
        if not force and not click.confirm(
            f"An exercise is already running on port {spec.port}. Replace it?"
        ):
            click.echo("Left the running exercise in place.")
            return
        _launch.stop_launch_on_port(launch_dir, spec.port)

    pid = _launch.spawn_detached(_launch.marimo_argv(spec), launch_dir)
    _launch.write_pidfile(
        launch_dir,
        _launch.PidfileEntry(
            pid=pid,
            exercise_id=spec.id,
            port=spec.port,
            mode=spec.mode,
        ),
    )
    click.echo(
        f"Launched `{spec.id}` ({spec.mode}) → http://localhost:{spec.port}"
    )
    click.echo(f"Stop it with: learningfoundry stop {spec.id}")


# ---------------------------------------------------------------------------
# stop
# ---------------------------------------------------------------------------

@main.command()
@click.argument("exercise_id", required=False)
@_launch_dir_option
@_log_level_option
def stop(exercise_id: str | None, launch_dir: Path, log_level: str) -> None:
    """Stop a launch-owned marimo notebook (all of them if no id is given)."""
    _setup_logging(level=log_level)

    from learningfoundry import launch as _launch

    launch_dir = _launch.resolve_manifest_dir(launch_dir)

    if exercise_id is not None:
        try:
            spec = _launch.resolve_launch_spec(launch_dir, exercise_id)
        except LaunchError as exc:
            click.echo(f"Stop error: {exc}", err=True)
            sys.exit(EXIT_VALIDATION)
        stopped = _launch.stop_launch_on_port(launch_dir, spec.port)
        if stopped is not None:
            click.echo(f"Stopped `{stopped.exercise_id}` (port {stopped.port}).")
        else:
            click.echo(f"No running exercise found for `{exercise_id}`.")
        return

    # No id → stop every launch-owned marimo.
    ports = _launch.launched_ports(launch_dir)
    if not ports:
        click.echo("No running exercises.")
        return
    for port in ports:
        stopped = _launch.stop_launch_on_port(launch_dir, port)
        if stopped is not None:
            click.echo(f"Stopped `{stopped.exercise_id}` (port {stopped.port}).")
