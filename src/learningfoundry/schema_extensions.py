# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Project-specific schema extensions for the three ``meta`` models
(Story J.h).

The base ``CurriculumMeta`` / ``ModuleMeta`` / ``LessonMeta`` ride on
``extra="allow"`` so authors can attach custom fields without a
learningfoundry schema change. That escape hatch is too permissive for
LLM-driven authoring — phantom fields (typos like ``prequisites``
instead of ``prerequisites``) get silently swallowed.

This module defines an optional ``learningfoundry-schema-extensions.yml``
contract that a project drops next to its ``curriculum.yml``. When the
file is present, ``build_extended_meta_models`` synthesizes strict
subclasses of the three meta models that declare the project's
additional fields and flip ``extra`` from ``allow`` to ``forbid`` (per
model, opt-out per model via ``extra: allow``).

When the file is absent, this module is not loaded into the parser
dispatch — today's ``extra="allow"`` behaviour is preserved exactly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    create_model,
    model_validator,
)

from .exceptions import SchemaExtensionError
from .schema_v1 import (
    CurriculumDef,
    CurriculumMeta,
    CurriculumV1,
    Lesson,
    LessonMeta,
    Module,
    ModuleMeta,
)


class _StrictExtModel(BaseModel):
    """Base for every schema-extension file model — typos in the
    extension file itself must fail loudly, since the whole point of the
    file is to tighten validation."""

    model_config = ConfigDict(extra="forbid")


class StrFieldDef(_StrictExtModel):
    type: Literal["str"]
    required: bool = True
    default: str | None = None


class IntFieldDef(_StrictExtModel):
    type: Literal["int"]
    required: bool = True
    default: int | None = None


class BoolFieldDef(_StrictExtModel):
    type: Literal["bool"]
    required: bool = True
    default: bool | None = None


class ListStrFieldDef(_StrictExtModel):
    type: Literal["list[str]"]
    required: bool = True
    default: list[str] | None = None


class EnumFieldDef(_StrictExtModel):
    type: Literal["enum"]
    values: list[str] = Field(min_length=1)
    required: bool = True
    default: str | None = None

    @model_validator(mode="after")
    def default_must_be_in_values(self) -> EnumFieldDef:
        if self.default is not None and self.default not in self.values:
            raise ValueError(
                f"enum default `{self.default}` is not in declared values "
                f"{self.values}"
            )
        return self


class ObjectFieldDef(_StrictExtModel):
    """Declares a single nested object — a structured dict with known
    field names. Authors recurse via ``fields:`` using the full
    ``FieldDef`` grammar (including nested ``object`` / ``list[object]``).

    No ``default:`` field is declared: a default object literal would be
    a footgun (mutable shared state, mismatched schema if fields change).
    Use ``required: false`` to make the whole object optional instead.
    Writing ``default: ...`` in the extension YAML is rejected by the
    ``extra="forbid"`` of ``_StrictExtModel``.
    """

    type: Literal["object"]
    fields: dict[str, FieldDef]
    required: bool = True
    extra: Literal["allow", "forbid"] = "forbid"


class ListObjectFieldDef(_StrictExtModel):
    """Declares a list of nested objects. The element type is built from
    ``fields:`` and named ``<parent>__<field>__Item`` so Pydantic error
    paths stay readable.

    Only ``default: []`` is meaningful — non-empty list defaults are
    rejected at load time (defaulting a list of structured objects would
    duplicate schema declarations and silently drift from the inline
    declaration). Use ``required: false`` if the field is optional.
    """

    type: Literal["list[object]"]
    fields: dict[str, FieldDef]
    required: bool = True
    extra: Literal["allow", "forbid"] = "forbid"
    default: list[Any] | None = None

    @model_validator(mode="after")
    def default_must_be_empty(self) -> ListObjectFieldDef:
        if self.default is not None and self.default != []:
            raise ValueError(
                f"list[object] default must be [] (empty list); "
                f"got {self.default!r}"
            )
        return self


FieldDef = Annotated[
    StrFieldDef
    | IntFieldDef
    | BoolFieldDef
    | ListStrFieldDef
    | EnumFieldDef
    | ObjectFieldDef
    | ListObjectFieldDef,
    Field(discriminator="type"),
]


# `ObjectFieldDef` and `ListObjectFieldDef` are declared before the
# `FieldDef` alias they reference inside `fields: dict[str, FieldDef]`.
# With `from __future__ import annotations` enabled at the top of this
# module, those annotations are strings until pydantic resolves them on
# first model use — `model_rebuild()` forces resolution now so any
# misuse (e.g. importing a stale model class before the alias exists)
# surfaces here rather than in user code with a confusing forward-ref
# error.
ObjectFieldDef.model_rebuild()
ListObjectFieldDef.model_rebuild()


SUPPORTED_FIELD_TYPES: tuple[str, ...] = (
    "str",
    "int",
    "bool",
    "list[str]",
    "enum",
    "object",
    "list[object]",
)


class MetaExtensions(_StrictExtModel):
    """Extensions for one meta model (``curriculum_meta``,
    ``module_meta``, or ``lesson_meta``).

    ``extra: forbid`` (the default when this section is present)
    converts the base meta model's permissive ``extra="allow"`` into
    strict whitelist-reject validation. Per-model ``extra: allow``
    restores today's behaviour for just that model — useful for staged
    rollouts where one meta layer is locked down while another is still
    being explored.
    """

    extra: Literal["forbid", "allow"] = "forbid"
    fields: dict[str, FieldDef] = Field(default_factory=dict)


class SchemaExtensions(_StrictExtModel):
    """Top-level model for ``learningfoundry-schema-extensions.yml``.

    Each ``*_meta`` section is independently optional — declaring
    ``lesson_meta`` does not require declaring ``curriculum_meta``.
    Sections that are absent leave their meta model untouched (base
    ``extra="allow"`` preserved).
    """

    version: Literal["1"]
    curriculum_meta: MetaExtensions | None = None
    module_meta: MetaExtensions | None = None
    lesson_meta: MetaExtensions | None = None


def _python_type_for(defn: FieldDef) -> Any:
    if isinstance(defn, StrFieldDef):
        return str
    if isinstance(defn, IntFieldDef):
        return int
    if isinstance(defn, BoolFieldDef):
        return bool
    if isinstance(defn, ListStrFieldDef):
        return list[str]
    if isinstance(defn, EnumFieldDef):
        return Literal[tuple(defn.values)]
    # `ObjectFieldDef` / `ListObjectFieldDef` are dispatched upstream in
    # `_object_field_entry`; they never reach this scalar-only resolver.
    raise SchemaExtensionError(  # pragma: no cover
        f"Internal error: _python_type_for called with "
        f"{type(defn).__name__}; object/list[object] dispatch must "
        "route through _object_field_entry."
    )


def _field_for(defn: FieldDef) -> tuple[Any, Any]:
    """Return ``(annotation, default)`` for ``pydantic.create_model``.

    Object variants (``ObjectFieldDef`` / ``ListObjectFieldDef``) are
    dispatched upstream in ``_object_field_entry``; reaching this scalar
    resolver with one indicates a routing bug and is raised loudly.

    Default resolution rules:
      * ``default:`` present → optional with that default (``required:``
        ignored — having a default *makes* the field optional).
      * ``default:`` absent and ``required: true`` (the default) → no
        default, value must be supplied (Pydantic ``...`` sentinel).
      * ``default:`` absent and ``required: false`` → optional, defaults
        to ``None`` (annotation widened to ``T | None``).
    """
    if isinstance(defn, ObjectFieldDef | ListObjectFieldDef):
        raise SchemaExtensionError(  # pragma: no cover
            f"Internal error: _field_for called with "
            f"{type(defn).__name__}; object/list[object] dispatch must "
            "route through _object_field_entry."
        )
    py_type = _python_type_for(defn)
    if defn.default is not None:
        return (py_type, defn.default)
    if defn.required:
        return (py_type, ...)
    return (py_type | None, None)


def _build_object_model(
    name: str,
    fields_def: dict[str, FieldDef],
    extra_mode: Literal["allow", "forbid"],
) -> type[BaseModel]:
    """Build a fresh Pydantic model from a YAML-declared ``object``
    schema. Nested ``object`` / ``list[object]`` fields recurse with
    deterministic names: ``<name>__<field>`` for nested objects and
    ``<name>__<field>__Item`` for the element type of nested lists.

    ``extra_mode`` is the synthesized model's ``model_config["extra"]``
    — ``"forbid"`` by default, ``"allow"`` when the YAML opts out.
    """
    field_defs: dict[str, tuple[Any, Any]] = {
        fname: _object_field_entry(name, fname, defn)
        for fname, defn in fields_def.items()
    }

    # `create_model` cannot take both `__base__` and `__config__`, so
    # synthesize a base with the desired `model_config` via `type()`
    # first, then layer fields on with `create_model`.
    intermediate = type(
        f"_{name}_Base",
        (BaseModel,),
        {"model_config": ConfigDict(extra=extra_mode)},
    )
    model: type[BaseModel] = create_model(  # type: ignore[call-overload]
        name,
        __base__=intermediate,
        **field_defs,
    )
    return model


def _object_field_entry(
    parent_name: str, field_name: str, defn: FieldDef
) -> tuple[Any, Any]:
    """Return ``(annotation, default)`` for one field, handling the
    recursive ``object`` / ``list[object]`` cases by delegating to
    ``_build_object_model`` and falling through to ``_field_for`` for
    every scalar variant.
    """
    if isinstance(defn, ObjectFieldDef):
        nested = _build_object_model(
            f"{parent_name}__{field_name}", defn.fields, defn.extra
        )
        if defn.required:
            return (nested, ...)
        return (nested | None, None)
    if isinstance(defn, ListObjectFieldDef):
        item = _build_object_model(
            f"{parent_name}__{field_name}__Item", defn.fields, defn.extra
        )
        if defn.default == []:
            return (list[item], [])  # type: ignore[valid-type]
        if defn.required:
            return (list[item], ...)  # type: ignore[valid-type]
        return (list[item] | None, None)  # type: ignore[valid-type]
    return _field_for(defn)


def _extend_one(
    base: type[BaseModel], ext: MetaExtensions | None
) -> type[BaseModel]:
    """Build an extended subclass of ``base`` with the declared fields
    appended and ``model_config["extra"]`` set to ``ext.extra``. Returns
    ``base`` unchanged when ``ext is None``."""
    if ext is None:
        return base

    # Pydantic's ``create_model`` cannot accept both ``__base__`` and
    # ``__config__``, so we synthesize an intermediate subclass via
    # ``type()`` to inject the new ``model_config`` first, then layer
    # the additional fields on top with ``create_model``.
    intermediate = type(
        f"_{base.__name__}_ExtraOverride",
        (base,),
        {"model_config": ConfigDict(extra=ext.extra)},
    )

    field_defs: dict[str, tuple[Any, Any]] = {
        name: _object_field_entry(base.__name__, name, defn)
        for name, defn in ext.fields.items()
    }
    extended: type[BaseModel] = create_model(  # type: ignore[call-overload]
        f"_Extended{base.__name__}",
        __base__=intermediate,
        **field_defs,
    )
    return extended


def build_extended_meta_models(
    extensions: SchemaExtensions,
) -> tuple[type[BaseModel], type[BaseModel], type[BaseModel]]:
    """Return ``(curriculum_meta_cls, module_meta_cls, lesson_meta_cls)``
    — each either the base model (when no extension is declared for it)
    or a strict subclass with the project's declared fields appended."""
    return (
        _extend_one(CurriculumMeta, extensions.curriculum_meta),
        _extend_one(ModuleMeta, extensions.module_meta),
        _extend_one(LessonMeta, extensions.lesson_meta),
    )


def build_extended_curriculum_v1(
    extensions: SchemaExtensions,
) -> type[CurriculumV1]:
    """Build a ``CurriculumV1`` subclass whose nested meta types are the
    extended variants from ``build_extended_meta_models``.

    Returns ``CurriculumV1`` unchanged when no section in ``extensions``
    declares any fields — the extended meta classes are the base
    classes, so nothing needs to be re-wired. Otherwise synthesizes the
    chain ``Lesson → Module → CurriculumDef → CurriculumV1``, overriding
    only the ``meta`` and ``lessons`` / ``modules`` / ``curriculum``
    field types as needed at each layer.

    The base ``@field_validator`` and ``@model_validator`` decorators on
    ``Lesson`` / ``Module`` / ``CurriculumDef`` are inherited by the
    synthesized subclasses unchanged (they operate on instance fields by
    name, not on type, so subclassed lesson lists validate identically).
    """
    cur_meta_cls, mod_meta_cls, les_meta_cls = build_extended_meta_models(extensions)

    if (
        cur_meta_cls is CurriculumMeta
        and mod_meta_cls is ModuleMeta
        and les_meta_cls is LessonMeta
    ):
        return CurriculumV1

    extended_lesson: type[Lesson] = Lesson
    if les_meta_cls is not LessonMeta:
        extended_lesson = create_model(
            "_ExtendedLesson",
            __base__=Lesson,
            meta=(les_meta_cls | None, None),
        )

    extended_module: type[Module] = Module
    module_overrides: dict[str, tuple[Any, Any]] = {}
    if mod_meta_cls is not ModuleMeta:
        module_overrides["meta"] = (mod_meta_cls | None, None)
    if extended_lesson is not Lesson:
        # `list[extended_lesson]` is a runtime-built generic alias; mypy
        # can't see that `extended_lesson` is a class at this point.
        module_overrides["lessons"] = (list[extended_lesson], ...)  # type: ignore[valid-type]
    if module_overrides:
        extended_module = create_model(  # type: ignore[call-overload]
            "_ExtendedModule",
            __base__=Module,
            **module_overrides,
        )

    extended_curriculum_def: type[CurriculumDef] = CurriculumDef
    curriculum_def_overrides: dict[str, tuple[Any, Any]] = {}
    if cur_meta_cls is not CurriculumMeta:
        curriculum_def_overrides["meta"] = (cur_meta_cls | None, None)
    if extended_module is not Module:
        curriculum_def_overrides["modules"] = (list[extended_module], ...)  # type: ignore[valid-type]
    if curriculum_def_overrides:
        extended_curriculum_def = create_model(  # type: ignore[call-overload]
            "_ExtendedCurriculumDef",
            __base__=CurriculumDef,
            **curriculum_def_overrides,
        )

    if extended_curriculum_def is CurriculumDef:
        return CurriculumV1

    extended_v1: type[CurriculumV1] = create_model(
        "_ExtendedCurriculumV1",
        __base__=CurriculumV1,
        curriculum=(extended_curriculum_def, ...),
    )
    return extended_v1


def load_schema_extensions(path: Path) -> SchemaExtensions:
    """Read and validate a schema-extensions YAML file. Raises
    ``SchemaExtensionError`` on any failure (missing, malformed YAML,
    schema-validation failure)."""
    try:
        with path.open() as f:
            data = yaml.safe_load(f)
    except FileNotFoundError as e:
        raise SchemaExtensionError(
            f"Schema extensions file not found: {path}"
        ) from e
    except yaml.YAMLError as e:
        raise SchemaExtensionError(
            f"Failed to parse schema extensions file {path}: {e}"
        ) from e
    if not isinstance(data, dict):
        raise SchemaExtensionError(
            f"Schema extensions file {path} must contain a YAML mapping "
            f"at the top level, got {type(data).__name__}."
        )
    try:
        return SchemaExtensions.model_validate(data)
    except ValidationError as e:
        raise SchemaExtensionError(
            f"Invalid schema extensions in {path}:\n{e}"
        ) from e
