# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Content resolver — resolves all content references in a parsed curriculum."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from learningfoundry.asset_resolver import Asset, resolve_markdown_assets
from learningfoundry.exceptions import ContentResolutionError
from learningfoundry.integrations.protocols import (
    ExerciseProvider,
    QuizProvider,
    VisualizationProvider,
)
from learningfoundry.schema_v1 import (
    CurriculumV1,
    ExerciseBlock,
    Lesson,
    Module,
    QuizBlock,
    TextBlock,
    VideoBlock,
    VisualizationBlock,
)

logger = logging.getLogger("learningfoundry.resolver")


@dataclass
class ResolvedContentBlock:
    type: str
    source: str | None
    ref: str | None
    content: dict[str, Any]


@dataclass
class ResolvedLesson:
    id: str
    title: str
    unlock_module_on_complete: bool = False
    content_blocks: list[ResolvedContentBlock] = field(default_factory=list)


@dataclass
class ResolvedModule:
    id: str
    title: str
    description: str
    locked: bool | None
    pre_assessment: dict[str, Any] | None
    post_assessment: dict[str, Any] | None
    lessons: list[ResolvedLesson] = field(default_factory=list)


@dataclass
class ResolvedCurriculum:
    version: str
    title: str
    description: str
    locking: dict[str, Any] = field(default_factory=dict)
    modules: list[ResolvedModule] = field(default_factory=list)
    # Image assets referenced from any text block's markdown, deduped by
    # content hash. Carried out-of-band — the generator copies these into
    # ``static/`` and they are stripped before curriculum.json is written
    # (the SvelteKit frontend never sees them).
    assets: list[Asset] = field(default_factory=list)


def resolve_curriculum(
    curriculum: CurriculumV1,
    base_dir: Path,
    quiz_provider: QuizProvider | None = None,
    exercise_provider: ExerciseProvider | None = None,
    visualization_provider: VisualizationProvider | None = None,
) -> ResolvedCurriculum:
    """Resolve all content references in a parsed curriculum.

    Args:
        curriculum: Validated ``CurriculumV1`` from the parser.
        base_dir: Root directory for resolving relative content paths.
        quiz_provider: Provider for ``quiz`` blocks. If None, uses
            ``QuizazzProvider`` (requires the ``quizazz`` package).
        exercise_provider: Provider for ``exercise`` blocks. If None, uses
            ``NbfoundryStub``.
        visualization_provider: Provider for ``visualization`` blocks. If None,
            uses ``D3foundryStub``.

    Returns:
        Fully resolved ``ResolvedCurriculum`` with all content inline.

    Raises:
        ContentResolutionError: Any block or assessment reference that cannot
            be resolved. Error message includes block location context.
    """
    if quiz_provider is None:
        from learningfoundry.integrations.quizazz import QuizazzProvider

        quiz_provider = QuizazzProvider()
    if exercise_provider is None:
        from learningfoundry.integrations.nbfoundry_stub import NbfoundryStub

        exercise_provider = NbfoundryStub()
    if visualization_provider is None:
        from learningfoundry.integrations.d3foundry_stub import D3foundryStub

        visualization_provider = D3foundryStub()

    resolved_modules: list[ResolvedModule] = []
    # Image assets are deduped globally on `dest_relative` (which is keyed
    # on the content hash), so a single image referenced from N lessons is
    # copied exactly once into the generated project.
    assets_by_dest: dict[str, Asset] = {}
    for module in curriculum.curriculum.modules:
        resolved_modules.append(
            _resolve_module(
                module,
                base_dir,
                quiz_provider,
                exercise_provider,
                visualization_provider,
                assets_by_dest,
            )
        )

    locking = curriculum.curriculum.locking
    locking_dict: dict[str, Any] = {
        "sequential": locking.sequential,
        "lesson_sequential": locking.lesson_sequential,
    }

    return ResolvedCurriculum(
        version=curriculum.version,
        title=curriculum.curriculum.title,
        description=curriculum.curriculum.description,
        locking=locking_dict,
        modules=resolved_modules,
        assets=list(assets_by_dest.values()),
    )


def _resolve_module(
    module: Module,
    base_dir: Path,
    quiz_provider: QuizProvider,
    exercise_provider: ExerciseProvider,
    visualization_provider: VisualizationProvider,
    assets_by_dest: dict[str, Asset],
) -> ResolvedModule:
    pre = None
    post = None
    if module.pre_assessment:
        pre = _resolve_assessment(
            module.pre_assessment.ref,
            base_dir,
            quiz_provider,
            location=f"module `{module.id}` pre_assessment",
        )
    if module.post_assessment:
        post = _resolve_assessment(
            module.post_assessment.ref,
            base_dir,
            quiz_provider,
            location=f"module `{module.id}` post_assessment",
        )

    resolved_lessons: list[ResolvedLesson] = []
    for lesson in module.lessons:
        resolved_lessons.append(
            _resolve_lesson(
                lesson,
                module.id,
                base_dir,
                quiz_provider,
                exercise_provider,
                visualization_provider,
                assets_by_dest,
            )
        )

    return ResolvedModule(
        id=module.id,
        title=module.title,
        description=module.description,
        locked=module.locked,
        pre_assessment=pre,
        post_assessment=post,
        lessons=resolved_lessons,
    )


def _resolve_lesson(
    lesson: Lesson,
    module_id: str,
    base_dir: Path,
    quiz_provider: QuizProvider,
    exercise_provider: ExerciseProvider,
    visualization_provider: VisualizationProvider,
    assets_by_dest: dict[str, Asset],
) -> ResolvedLesson:
    resolved_blocks: list[ResolvedContentBlock] = []
    for idx, block in enumerate(lesson.content_blocks):
        location = f"module `{module_id}` / lesson `{lesson.id}` / block[{idx}]"
        resolved_blocks.append(
            _resolve_block(
                block,
                base_dir,
                quiz_provider,
                exercise_provider,
                visualization_provider,
                location,
                assets_by_dest,
            )
        )
    return ResolvedLesson(
        id=lesson.id,
        title=lesson.title,
        unlock_module_on_complete=lesson.unlock_module_on_complete,
        content_blocks=resolved_blocks,
    )


def _resolve_block(
    block: TextBlock | VideoBlock | QuizBlock | ExerciseBlock | VisualizationBlock,
    base_dir: Path,
    quiz_provider: QuizProvider,
    exercise_provider: ExerciseProvider,
    visualization_provider: VisualizationProvider,
    location: str,
    assets_by_dest: dict[str, Asset],
) -> ResolvedContentBlock:
    try:
        if isinstance(block, TextBlock):
            return _resolve_text(block, base_dir, location, assets_by_dest)
        if isinstance(block, VideoBlock):
            return _resolve_video(block, location)
        if isinstance(block, QuizBlock):
            manifest = quiz_provider.compile_assessment(
                Path(block.ref), base_dir
            )
            manifest["pass_threshold"] = block.pass_threshold
            return ResolvedContentBlock(
                type="quiz", source=block.source, ref=block.ref, content=manifest
            )
        if isinstance(block, ExerciseBlock):
            content = exercise_provider.compile_exercise(Path(block.ref), base_dir)
            return ResolvedContentBlock(
                type="exercise", source=block.source, ref=block.ref, content=content
            )
        if isinstance(block, VisualizationBlock):
            content = visualization_provider.compile_visualization(
                Path(block.ref), base_dir
            )
            return ResolvedContentBlock(
                type="visualization",
                source=block.source,
                ref=block.ref,
                content=content,
            )
    except ContentResolutionError:
        raise
    except Exception as exc:
        raise ContentResolutionError(
            f"{location}: failed to resolve block — {exc}"
        ) from exc

    raise ContentResolutionError(f"{location}: unknown block type `{block.type}`")


def _resolve_text(
    block: TextBlock,
    base_dir: Path,
    location: str,
    assets_by_dest: dict[str, Asset],
) -> ResolvedContentBlock:
    content_path = base_dir / block.ref
    try:
        text = content_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ContentResolutionError(
            f"{location}: markdown file not found: `{content_path}`"
        ) from exc

    if not text.strip():
        logger.warning("%s: markdown file `%s` is empty.", location, content_path)

    # Scan for image refs, copy-relative on disk, rewrite to absolute
    # `/content/<hash>/<basename>` URLs that work at any SvelteKit route.
    # Missing images surface as ContentResolutionError tagged with the
    # block location for parity with other resolution errors.
    try:
        rewritten, lesson_assets = resolve_markdown_assets(text, content_path)
    except ContentResolutionError as exc:
        raise ContentResolutionError(f"{location}: {exc}") from exc

    for asset in lesson_assets:
        # Dedup globally — two lessons referencing the same image hash to
        # the same dest_relative, so the dict swallows the duplicate.
        assets_by_dest.setdefault(asset.dest_relative, asset)

    return ResolvedContentBlock(
        type="text",
        source=None,
        ref=block.ref,
        content={"markdown": rewritten, "path": str(content_path)},
    )


def _resolve_video(block: VideoBlock, location: str) -> ResolvedContentBlock:
    return ResolvedContentBlock(
        type="video",
        source=None,
        ref=None,
        content={
            "url": block.url,
            "provider": block.provider,
            "extensions": block.extensions,
        },
    )


def _resolve_assessment(
    ref: str,
    base_dir: Path,
    quiz_provider: QuizProvider,
    location: str,
) -> dict[str, Any]:
    try:
        return quiz_provider.compile_assessment(Path(ref), base_dir)
    except Exception as exc:
        raise ContentResolutionError(
            f"{location}: failed to compile assessment `{ref}` — {exc}"
        ) from exc
