# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Content resolver — resolves all content references in a parsed curriculum."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from learningfoundry.asset_resolver import Asset, resolve_markdown_assets
from learningfoundry.directives import lint_directives
from learningfoundry.exceptions import ContentResolutionError
from learningfoundry.integrations.protocols import (
    AssessmentProvider,
    ExerciseProvider,
    VisualizationProvider,
)
from learningfoundry.schema_v1 import (
    AfterLesson,
    AssessmentBlock,
    AssessmentDefinition,
    BeforeLesson,
    CurriculumV1,
    ExerciseBlock,
    Lesson,
    Module,
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
    meta: dict[str, Any] | None = None
    content_blocks: list[ResolvedContentBlock] = field(default_factory=list)


@dataclass
class ResolvedAssessment:
    """A single resolved assessment, ready for emission to ``curriculum.json``.

    ``position`` is preserved as a JSON-friendly value (string for
    ``"before_lessons"`` / ``"after_lessons"``; single-key mapping for
    the lesson-anchored variants) so the SvelteKit frontend can interleave
    each assessment relative to lessons at render time. The order of
    ``ResolvedModule.assessments`` is the canonical iteration order
    (Story J.e).
    """

    id: str
    role: str
    position: str | dict[str, str]
    source: str
    ref: str
    pass_threshold: float | None
    content: dict[str, Any]


@dataclass
class ResolvedModule:
    id: str
    title: str
    description: str
    locked: bool | None
    meta: dict[str, Any] | None = None
    assessments: list[ResolvedAssessment] = field(default_factory=list)
    lessons: list[ResolvedLesson] = field(default_factory=list)


@dataclass
class ResolvedCurriculum:
    version: str
    title: str
    description: str
    locking: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] | None = None
    modules: list[ResolvedModule] = field(default_factory=list)
    # Image assets referenced from any text block's markdown, deduped by
    # content hash. Carried out-of-band — the generator copies these into
    # ``static/`` and they are stripped before curriculum.json is written
    # (the SvelteKit frontend never sees them).
    assets: list[Asset] = field(default_factory=list)


def resolve_curriculum(
    curriculum: CurriculumV1,
    base_dir: Path,
    assessment_provider: AssessmentProvider | None = None,
    exercise_provider: ExerciseProvider | None = None,
    visualization_provider: VisualizationProvider | None = None,
) -> ResolvedCurriculum:
    """Resolve all content references in a parsed curriculum.

    Args:
        curriculum: Validated ``CurriculumV1`` from the parser.
        base_dir: Root directory for resolving relative content paths.
        assessment_provider: Provider for assessment blocks. If None, uses
            ``QuizazzProvider`` (requires the ``quizazz`` package).
        exercise_provider: Provider for ``ready`` ``exercise`` blocks. If None,
            uses ``NbfoundryProvider`` (requires the ``nbfoundry`` package).
            ``stub`` blocks bypass the provider entirely (Story K.d).
        visualization_provider: Provider for ``visualization`` blocks. If None,
            uses ``D3foundryStub``.

    Returns:
        Fully resolved ``ResolvedCurriculum`` with all content inline.

    Raises:
        ContentResolutionError: Any block or assessment reference that cannot
            be resolved. Error message includes block location context.
    """
    if assessment_provider is None:
        from learningfoundry.integrations.quizazz import QuizazzProvider

        assessment_provider = QuizazzProvider()
    if exercise_provider is None:
        from learningfoundry.integrations.nbfoundry import NbfoundryProvider

        exercise_provider = NbfoundryProvider()
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
                assessment_provider,
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
        meta=(
            curriculum.curriculum.meta.model_dump()
            if curriculum.curriculum.meta is not None
            else None
        ),
        modules=resolved_modules,
        assets=list(assets_by_dest.values()),
    )


def _resolve_module(
    module: Module,
    base_dir: Path,
    assessment_provider: AssessmentProvider,
    exercise_provider: ExerciseProvider,
    visualization_provider: VisualizationProvider,
    assets_by_dest: dict[str, Asset],
) -> ResolvedModule:
    resolved_lessons: list[ResolvedLesson] = []
    for lesson in module.lessons:
        resolved_lessons.append(
            _resolve_lesson(
                lesson,
                module.id,
                base_dir,
                assessment_provider,
                exercise_provider,
                visualization_provider,
                assets_by_dest,
            )
        )

    resolved_assessments = _resolve_assessments(
        module, base_dir, assessment_provider
    )

    return ResolvedModule(
        id=module.id,
        title=module.title,
        description=module.description,
        locked=module.locked,
        meta=module.meta.model_dump() if module.meta is not None else None,
        assessments=resolved_assessments,
        lessons=resolved_lessons,
    )


def _resolve_assessments(
    module: Module,
    base_dir: Path,
    assessment_provider: AssessmentProvider,
) -> list[ResolvedAssessment]:
    """Resolve every assessment defined on the module and emit them in
    canonical placement order (Story J.e).

    Order rule, materialized once here so downstream consumers don't
    re-derive it:

    1. All ``position == "before_lessons"`` assessments, in author order.
    2. For each lesson in ``module.lessons`` (in author order):
       a. ``BeforeLesson`` assessments anchored to that lesson, in author
          order.
       b. ``AfterLesson`` assessments anchored to that lesson, in author
          order.
    3. All ``position == "after_lessons"`` assessments, in author order.

    Lesson-anchored refs whose target lesson does not exist were already
    rejected by ``Module.validate_assessment_lesson_refs`` at parse time.
    """
    before_all: list[AssessmentDefinition] = []
    after_all: list[AssessmentDefinition] = []
    by_before_id: dict[str, list[AssessmentDefinition]] = {}
    by_after_id: dict[str, list[AssessmentDefinition]] = {}

    for assessment in module.assessments:
        pos = assessment.position
        if pos == "before_lessons":
            before_all.append(assessment)
        elif pos == "after_lessons":
            after_all.append(assessment)
        elif isinstance(pos, BeforeLesson):
            by_before_id.setdefault(pos.before_lesson, []).append(assessment)
        elif isinstance(pos, AfterLesson):
            by_after_id.setdefault(pos.after_lesson, []).append(assessment)

    ordered: list[AssessmentDefinition] = []
    ordered.extend(before_all)
    for lesson in module.lessons:
        ordered.extend(by_before_id.get(lesson.id, []))
        ordered.extend(by_after_id.get(lesson.id, []))
    ordered.extend(after_all)

    resolved: list[ResolvedAssessment] = []
    for assessment in ordered:
        location = (
            f"module `{module.id}` assessment role=`{assessment.role}`"
        )
        content = _resolve_assessment(
            assessment.ref, base_dir, assessment_provider, location
        )
        assert assessment.id is not None  # auto-gen guarantees this
        resolved.append(
            ResolvedAssessment(
                id=assessment.id,
                role=assessment.role,
                position=_position_to_jsonable(assessment.position),
                source=assessment.source,
                ref=assessment.ref,
                pass_threshold=assessment.pass_threshold,
                content=content,
            )
        )
    return resolved


def _position_to_jsonable(
    position: str | BeforeLesson | AfterLesson,
) -> str | dict[str, str]:
    if isinstance(position, BeforeLesson):
        return {"before_lesson": position.before_lesson}
    if isinstance(position, AfterLesson):
        return {"after_lesson": position.after_lesson}
    return position


def _resolve_lesson(
    lesson: Lesson,
    module_id: str,
    base_dir: Path,
    assessment_provider: AssessmentProvider,
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
                assessment_provider,
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
        meta=lesson.meta.model_dump() if lesson.meta is not None else None,
        content_blocks=resolved_blocks,
    )


def _resolve_block(
    block: (
        TextBlock | VideoBlock | AssessmentBlock | ExerciseBlock | VisualizationBlock
    ),
    base_dir: Path,
    assessment_provider: AssessmentProvider,
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
        if isinstance(block, AssessmentBlock):
            manifest = assessment_provider.compile_assessment(
                Path(block.ref), base_dir
            )
            manifest["pass_threshold"] = block.pass_threshold
            return ResolvedContentBlock(
                type="assessment", source=block.source, ref=block.ref, content=manifest
            )
        if isinstance(block, ExerciseBlock):
            # Single `status` switch (Story K.d). `stub` → placeholder dict
            # via the shared factory; no provider call, so an all-stub
            # curriculum never imports nbfoundry. `ready` (default) compiles
            # via the provider and fails loud on a bad ref (no stub fallback).
            if block.status == "stub":
                from learningfoundry.integrations.nbfoundry_stub import stub_exercise

                content = stub_exercise(Path(block.ref))
            else:
                content = exercise_provider.compile_exercise(Path(block.ref), base_dir)
                # Stage asset files the compiled exercise references (Story
                # K.e). They travel as relative paths in `assets: list[str]`
                # and land under the exercise's `id` namespace
                # (`static/exercises/<id>/<path>`), deduped on `dest_relative`
                # via the shared aggregator. `block.id` is guaranteed by the
                # schema's auto-gen validator.
                for rel in content.get("assets") or []:
                    dest_relative = f"exercises/{block.id}/{rel}"
                    assets_by_dest.setdefault(
                        dest_relative,
                        Asset(source=base_dir / rel, dest_relative=dest_relative),
                    )
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

    # Lint tutorial-scaffold directives (Story J.d.2). Catches an
    # unbalanced `::: worked-example` / `::: faded-example` /
    # `::: independent-practice` block here so authors get a build-time
    # error rather than a silent render-time anomaly.
    lint_directives(text, location)

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
    assessment_provider: AssessmentProvider,
    location: str,
) -> dict[str, Any]:
    try:
        return assessment_provider.compile_assessment(Path(ref), base_dir)
    except Exception as exc:
        raise ContentResolutionError(
            f"{location}: failed to compile assessment `{ref}` — {exc}"
        ) from exc
