# LearningFoundry spec: add two types

`object` and `list[object]` as separate discriminated-union variants. Consistent with the existing grammar (`str` vs. `list[str]` is already the precedent), and both shapes have legitimate use cases — the `phases` and `citations` are both `list[object]`, but a single nested object covers things like a `provenance: {author, license}` field that we might want at a lesson level.

## Why "object," not "dict" or "nested_object"

- **`dict`** — implies arbitrary keys (`Mapping[str, V]`). What you actually want is a structured type with known field names — that's an "object" in JSON-Schema parlance.
- **`nested_object`** — the "nested" prefix is redundant; every object declared in an extensions file is nested by definition (it's inside a `fields:` map). Extra ceremony with no extra meaning.
- **`object`** — matches JSON Schema, reads naturally as `list[object]`, and stays terse like the existing `str`/`int`/`bool` siblings.

## Proposed grammar

```yaml
curriculum_meta:
  fields:
    # list[object] — citations
    citations:
      type: list[object]
      fields:
        key:      { type: str }
        apa:      { type: str }
        doi:      { type: str, required: false }
        verified: { type: bool }
        role:     { type: str, required: false }
        note:     { type: str, required: false }

    # list[object] — phases (one of the fields is itself list[str])
    phases:
      type: list[object]
      fields:
        id:          { type: str }
        title:       { type: str }
        description: { type: str }
        modules:     { type: list[str] }

lesson_meta:
  fields:
    # single object — example, not from your file
    provenance:
      type: object
      required: false
      fields:
        author:  { type: str }
        license: { type: str }
```

Key properties of this design:

- **Recursive `fields:` map.** Every `object` (and `list[object]`) carries its own `fields:` block whose entries reuse the full `FieldDef` grammar, including nested `object` types. Arbitrary nesting depth comes free; readability problems at depth 5+ are the author's to manage.
- **`extra: forbid` by default at every level**, matching the top-level extension contract. Per-object `extra: allow` opt-out for staged tightening — same posture as the existing meta-model knobs.
- **Standard `required: bool` and `default:` semantics.** For `list[object]`, only `default: []` is meaningful (don't try to parse object literals as defaults). For `object`, treat `default:` as unsupported — use `required: false` instead. Loud errors on either at load time.

## Implementation sketch (for the learningfoundry PR)

In `schema_extensions.py`:

1. Two new discriminated-union variants:
   - `ObjectFieldDef`: `type: Literal["object"]`, `fields: dict[str, FieldDef]`, `required: bool = True`, plus optional `extra: Literal["allow", "forbid"] = "forbid"`.
   - `ListObjectFieldDef`: `type: Literal["list[object]"]`, `fields: dict[str, FieldDef]`, `required: bool = True`, `default: list | None = None` (only `[]` accepted at load time).
2. Recursive `_build_object_model(name: str, fields: dict, extra: str) -> type[BaseModel]` using `create_model`, called from `_python_type_for` for both new variants.
3. Deterministic nested-model naming so Pydantic error paths stay readable: `CurriculumMeta__citations__Item`, `CurriculumMeta__phases__Item`, `LessonMeta__provenance`.
4. Add `"object"` and `"list[object]"` to `SUPPORTED_FIELD_TYPES`.
5. Update README's "Strict project-specific extensions" section with `list[object]` and `object` examples — your `citations` declaration is the natural worked example.

## One sharp edge to call out in the PR

`FieldDef` is currently a *flat* discriminated union over `Annotated[StrFieldDef | IntFieldDef | ... , Field(discriminator="type")]`. Adding recursion means `ObjectFieldDef.fields: dict[str, FieldDef]` is a forward reference into the same union. Pydantic v2 supports this via `model_rebuild()` after the union alias is declared. Worth noting in the PR description because the failure mode (forward-ref not resolved) gives a confusing error.

## Bonus: why this generalizes well

Once `object` and `list[object]` land, the extension grammar is complete enough to express any tree-shaped data — which means future authoring needs (per-module learning objectives as `list[object]` with `bloom`/`text` fields, structured `assessments[]` overrides, etc.) don't trigger another schema-extensions feature request. The grammar becomes essentially a typed-JSON subset, with `enum` as the one non-trivial constraint type.

Want me to draft the actual PR diff against learningfoundry, or sketch the README-section update first so you can see the user-facing shape before committing to the implementation?
