# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0

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
)
from learningfoundry.logging_config import setup_logging as _setup_logging

# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------
EXIT_VALIDATION = 1
EXIT_RESOLUTION = 2
EXIT_GENERATION = 3
EXIT_CONFIG = 4


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


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

@main.command()
@_config_option
@_log_level_option
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
    output_dir: Path,
    base_dir: Path | None,
) -> None:
    """Parse → resolve → generate a SvelteKit project."""
    _setup_logging(level=log_level)

    from learningfoundry.pipeline import run_build

    try:
        run_build(config_path, output_dir, base_dir=base_dir)
    except (CurriculumValidationError, CurriculumVersionError) as exc:
        click.echo(f"Validation error: {exc}", err=True)
        sys.exit(EXIT_VALIDATION)
    except ContentResolutionError as exc:
        click.echo(f"Content resolution error: {exc}", err=True)
        sys.exit(EXIT_RESOLUTION)
    except GenerationError as exc:
        click.echo(f"Generation error: {exc}", err=True)
        sys.exit(EXIT_GENERATION)
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
    base_dir: Path | None,
) -> None:
    """Validate a curriculum YAML without generating output."""
    _setup_logging(level=log_level)

    from learningfoundry.pipeline import run_validate

    try:
        is_valid, errors = run_validate(config_path, base_dir=base_dir)
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
    except ConfigError as exc:
        click.echo(f"Config error: {exc}", err=True)
        sys.exit(EXIT_CONFIG)

    click.echo(f"Preview server started at http://localhost:{port}")
