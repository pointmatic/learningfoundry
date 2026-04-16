# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""SvelteKit project generator — copies template and writes curriculum.json."""

import dataclasses
import json
import logging
import shutil
import tempfile
from pathlib import Path

from learningfoundry.exceptions import GenerationError
from learningfoundry.resolver import ResolvedCurriculum

logger = logging.getLogger("learningfoundry.generator")

_TEMPLATE_DIR = Path(__file__).parent / "sveltekit_template"


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
        logger.warning(
            "Output directory `%s` already exists and will be overwritten.",
            output_dir,
        )

    _atomic_copy(src, output_dir)
    _write_curriculum_json(resolved, output_dir)

    logger.info("Generated SvelteKit project at: %s", output_dir)


def _atomic_copy(src: Path, dst: Path) -> None:
    """Copy src tree to dst atomically via a sibling temp directory."""
    parent = dst.parent
    parent.mkdir(parents=True, exist_ok=True)

    try:
        with tempfile.TemporaryDirectory(dir=parent, prefix=".lf_gen_") as tmp_str:
            tmp = Path(tmp_str) / dst.name
            shutil.copytree(src, tmp)
            if dst.exists():
                shutil.rmtree(dst)
            tmp.rename(dst)
    except OSError as exc:
        raise GenerationError(
            f"Failed to generate project at `{dst}`: {exc}"
        ) from exc


def _write_curriculum_json(resolved: ResolvedCurriculum, output_dir: Path) -> None:
    """Serialize ResolvedCurriculum to output_dir/static/curriculum.json."""
    static_dir = output_dir / "static"
    static_dir.mkdir(parents=True, exist_ok=True)

    curriculum_json = output_dir / "static" / "curriculum.json"
    try:
        data = dataclasses.asdict(resolved)
        curriculum_json.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise GenerationError(
            f"Failed to write curriculum.json to `{curriculum_json}`: {exc}"
        ) from exc

    logger.debug("Wrote curriculum.json (%d bytes)", curriculum_json.stat().st_size)
