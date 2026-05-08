# learningfoundry — Improvement Plan

A draft roadmap targeting the pedagogical-friction gaps surfaced while building the CNN curriculum prompt. Scoped for additive changes that bump v1 to v1.1 — no breaking changes, no v2 migration required.

---

## Goals

1. Restore structured pedagogical metadata that the lean v1 schema had to drop (role, hook, image_prompt, objectives, terms_introduced/reinforced).
2. Make the three-assessment pedagogy (pre / practice / post) first-class, with positional flexibility so practice quizzes can land mid-module.
3. Recognize the tutorial scaffold (worked → faded → independent) as a structured pattern instead of a prose convention.
4. Support varied curriculum styles via configurable meta templates so the engine isn't opinionated about pedagogy out of the box.

These are sequenced from highest-leverage / smallest-cost to lowest. The first two unblock the CNN curriculum work today; the rest can land over weeks.

---

## Recommended Order

| # | Feature | Effort | Unblocks |
|---|---------|--------|----------|
| 1 | Lesson + module `meta` blocks | ~1–2 days | Curriculum prompt's structured pedagogy; teaser rendering; image-gen pipeline; distribution audits |
| 2 | Tutorial scaffold via markdown directives | ~1 day | Tutorial lesson consistency; styled rendering |
| 3 | Generalized `assessments` array (replaces / extends pre/post) | ~2–3 days | Practice quizzes; positional flexibility; cleaner authoring |
| 4 | Configurable curriculum-style templates | ~3–5 days | Multi-style support; validation per style; reusable across curricula |

---

## 1. Lesson + Module `meta` Blocks

### Rationale

Pedagogical metadata (role, hook, objectives, etc.) currently has nowhere to live in the schema. The CNN curriculum prompt smuggles it into HTML comments and fenced code blocks, which is invisible to the build pipeline. A first-class `meta` block fixes this without making the metadata mandatory.

### Schema

Add an optional typed `meta` field at module and lesson level. Use Pydantic with `extra = "allow"` so authors can add their own fields without schema changes.

```yaml
modules:
  - id: mod-01
    title: "Module 1"
    description: "..."
    meta:
      theme: "Why convolutions exist"
      big_problem: "Fully-connected networks ignore the structure of images."
      objectives:
        - "Explain why FC nets fail on images"
        - "Describe the role of weight sharing"
      experiential_summary: "Build your first conv layer in PyTorch."
      target_audience: "Intermediate Python; high-school math"

    lessons:
      - id: lesson-01
        title: "Lesson 1"
        meta:
          role: opener           # opener | concept | story | math | tutorial | practice | hands_on | bonus
          hook:
            tagline: "What if your first layer of vision was just a flashlight on the world?"
            image_prompt: "A 1960s neuroscience lab; oscilloscope tracing a single spike."
          terms_introduced: [receptive_field, simple_cells]
          terms_reinforced: []
          duration_minutes: 15
        content_blocks: [...]
```

### Pydantic models (sketch)

```python
# schema_v1.py — additions

class Hook(BaseModel):
    tagline: str
    image_prompt: Optional[str] = None
    class Config: extra = "allow"

class LessonMeta(BaseModel):
    role: Optional[str] = None  # open string; styles can constrain (see Feature 4)
    hook: Optional[Hook] = None
    terms_introduced: List[str] = Field(default_factory=list)
    terms_reinforced: List[str] = Field(default_factory=list)
    duration_minutes: Optional[int] = None
    class Config: extra = "allow"

class ModuleMeta(BaseModel):
    theme: Optional[str] = None
    big_problem: Optional[str] = None
    objectives: List[str] = Field(default_factory=list)
    experiential_summary: Optional[str] = None
    class Config: extra = "allow"

# Attach to existing Module / Lesson models:
class Lesson(BaseModel):
    id: str
    title: str
    meta: Optional[LessonMeta] = None
    content_blocks: List[ContentBlock]
    # ...

class Module(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    meta: Optional[ModuleMeta] = None
    # ... pre_assessment, post_assessment, lessons
```

### Files affected

- `src/learningfoundry/schema_v1.py` — add `Hook`, `LessonMeta`, `ModuleMeta`; wire onto `Lesson` / `Module`.
- `src/learningfoundry/generator.py` — pass `meta` through into `curriculum.json`.
- `sveltekit_template/` — render lesson `meta.role` as a small chip in the sidebar/breadcrumb; render `meta.hook.tagline` at the top of the lesson body (or as a teaser card on the module index page).
- `tests/` — schema acceptance + roundtrip tests.

### Notes

- `role` stays an open string in the base schema. Style templates (Feature 4) can constrain to an enum.
- `terms_introduced` / `terms_reinforced` enable a future `learningfoundry audit` command that flags terms introduced but never reinforced.
- The `hook.image_prompt` field is purely metadata for v1.1 — no rendering pipeline yet. Future: a `learningfoundry generate-images` command that walks every lesson, runs each prompt through an image API, and writes the result back to the lesson's image directory.

---

## 2. Tutorial Scaffold via Markdown Directives

### Rationale

The worked → faded → independent practice pattern is high-leverage in technical curricula but currently survives only as a prose convention. Recognizing it in the markdown gives consistent rendering, validation, and future affordances (e.g., progressive reveal, hint toggles).

### Mechanism

Use markdown container directives (already common in MkDocs, MDX, and others). Pick a markdown-it plugin that supports them (`markdown-it-container` or equivalent for the SvelteKit toolchain).

```markdown
::: worked-example
Compute the output shape for a 32×32 input with a 3×3 kernel, stride 1, padding 0.

We apply (W − K + 2P) / S + 1 = (32 − 3 + 0) / 1 + 1 = 30. Output: 30×30.
:::

::: faded-example
For a 64×64 input with a 5×5 kernel, stride 1, padding 2 — what's the output shape?

(_The formula is yours to apply._)
:::

::: independent-practice
Given a 28×28 input, design a Conv2d that produces 14×14 output. State your kernel size, stride, and padding.
:::
```

### Files affected

- `sveltekit_template/` — markdown renderer config + CSS for the three directive types (distinct visual treatment: worked = filled card; faded = outlined card with reduced contrast; independent = challenge prompt with a checkmark affordance).
- Optional `src/learningfoundry/parser.py` — add a markdown lint pass at validation time that flags malformed directives or unbalanced opens/closes.
- `docs/` — author-facing docs on the directive syntax.

### Notes

- Directives are content-block-agnostic — they live inside a `text` block's markdown. No new content block type needed.
- A future `tutorial` content block type could enforce structure programmatically, but that adds schema weight. Markdown directives are the lighter touch and keep the lesson body in one file.

---

## 3. Generalized `assessments` Array

### Rationale

Today's `pre_assessment` / `post_assessment` covers two of the three pedagogically interesting positions. Practice quizzes (post-knowledge / pre-experiential) have to be smuggled in as lesson-level `quiz` content blocks, which makes the three-quiz model asymmetric: pre/post live at module level, practice lives inside the lesson list. A generalized assessments array unifies all three under one mental model and opens the door to checkpoints, mid-module probes, etc.

### Schema

```yaml
modules:
  - id: mod-01
    title: "..."

    assessments:
      - role: pre
        position: before_lessons
        source: quizazz
        ref: assessments/mod-01-pre.yml
        # pass_threshold optional; pre is typically priming, no gating

      - role: practice
        position:
          before_lesson: lesson-07   # the hands-on lesson
        source: quizazz
        ref: assessments/mod-01-practice.yml
        pass_threshold: 0.7

      - role: post
        position: after_lessons
        source: quizazz
        ref: assessments/mod-01-post.yml
        pass_threshold: 0.8

    lessons: [...]
```

### Position grammar

- `before_lessons` (semantic; before any lesson)
- `after_lessons` (semantic; after all lessons)
- `{ before_lesson: <lesson-id> }` (positional)
- `{ after_lesson: <lesson-id> }` (positional)

The parser resolves positional refs against the module's `lessons` array and errors if a referenced lesson id doesn't exist.

### Backward compatibility

Keep `pre_assessment` and `post_assessment` as deprecated aliases. The parser converts them into entries in `assessments`:

```python
# parser.py
if module.pre_assessment is not None:
    module.assessments.insert(0, AssessmentDefinition(
        role="pre",
        position="before_lessons",
        **module.pre_assessment.dict(),
    ))
    warnings.warn(
        f"Module {module.id}: pre_assessment is deprecated; use assessments[].",
        DeprecationWarning,
    )
```

Same for `post_assessment` → appended with `position: after_lessons`. Existing curricula keep working with a deprecation warning.

### Files affected

- `src/learningfoundry/schema_v1.py` — add `AssessmentDefinition` model with discriminated-union `position`.
- `src/learningfoundry/parser.py` — backward-compat shim; positional resolution.
- `src/learningfoundry/pipeline.py` — assessment ordering when generating the SvelteKit module flow.
- `sveltekit_template/` — render assessments at their resolved positions in the lesson list.
- `tests/` — backward-compat tests; positional resolution tests; error cases (unknown lesson id).

### Notes

- `role` is open string in the schema. `pre`, `practice`, `post`, and `checkpoint` are conventional.
- `pass_threshold` semantics may differ by role (pre is rarely gated; post often is). The schema doesn't enforce — that's a curriculum-style concern (Feature 4).

---

## 4. Configurable Curriculum-Style Templates

### Rationale

Different curriculum genres want different pedagogical commitments. A boot-camp curriculum might require every lesson to declare a duration and a role; a self-study curriculum might require nothing. Hard-coding required meta in the schema is wrong for both. A style template is a curriculum-level config that declares which meta fields are required, which roles are allowed, and which assessment positions are expected.

### Schema

Add a top-level `style` field on the curriculum:

```yaml
curriculum:
  title: "..."
  style: narrative-survey         # built-in
  # or:
  # style: ./styles/my-custom-style.yml
```

A style file looks like:

```yaml
# styles/narrative-survey.yml
name: "Narrative Survey"
description: "Story-driven curriculum with strong meta requirements."

module_meta:
  required: [theme, big_problem, objectives]
  optional: [experiential_summary, target_audience]

lesson_meta:
  required: [role, hook]
  optional: [image_prompt, terms_introduced, terms_reinforced, duration_minutes]
  allowed_roles:
    - opener
    - concept
    - story
    - math
    - tutorial
    - practice
    - hands_on
    - bonus

assessments:
  required_roles: [pre, practice, post]    # every module must have one of each
  allowed_positions:
    pre: [before_lessons]
    practice: [{ before_lesson: "*" }]     # any lesson
    post: [after_lessons]
```

### Built-in styles to ship with v1.1

- `minimal` — no meta required, no assessment expectations. The current default.
- `narrative-survey` — opinionated meta, three-quiz model expected. Matches the CNN curriculum prompt.

Authors can author their own style files and reference them by relative path.

### Validation

`learningfoundry validate` runs style-level checks after schema-level checks:

- Every required meta field present?
- Every lesson role in `allowed_roles`?
- Every required assessment role present per module?
- Every assessment position within `allowed_positions[role]`?

Errors point to the offending module/lesson and the style rule violated.

### Files affected

- `src/learningfoundry/styles.py` (new) — load built-in styles, resolve `style:` field, run validation.
- `src/learningfoundry/styles/` (new) — built-in YAML style files (`minimal.yml`, `narrative-survey.yml`).
- `src/learningfoundry/parser.py` — invoke style validation after schema validation.
- `src/learningfoundry/cli.py` — surface style validation errors with file/line context.
- `tests/` — fixtures for each built-in style; custom-style loading tests.
- `docs/` — author-facing docs on style files.

### Notes

- Styles are versioned implicitly via the package version; a future change to `narrative-survey.yml` shows up when the user upgrades. If this becomes painful, add a `style_version` field.
- Custom styles live in the curriculum repo and are version-controlled with the curriculum.
- A style is *additive* — it can require fields and constrain values, but cannot relax schema-level requirements.

---

## Cross-Cutting Concerns

### Versioning

All four features are additive. Bump curriculum schema to `version: "1.1.0"`. The parser accepts both `1.0.0` and `1.1.0`. New fields are optional in `1.0.0` (with deprecation warnings for `pre_assessment` / `post_assessment` once Feature 3 lands).

A v2 bump is *not* needed for any of this. Reserve v2 for breaking changes (e.g., dropping the deprecated assessment aliases, or restructuring content_blocks).

### Frontend rendering

Each feature has a frontend slice. Worth doing the SvelteKit work in lockstep with each schema change so curricula authored against v1.1 actually look different in the rendered app. Otherwise the meta is a write-only graveyard for two features running.

### Tests

Each feature gets:

- **Schema acceptance**: valid inputs parse, invalid inputs fail with useful messages.
- **Backward compatibility**: old curricula still work (with deprecation warnings where applicable).
- **Generator output**: `curriculum.json` contains the expected fields.
- **SvelteKit smoke**: rendered app contains the expected DOM elements (role chips, hook taglines, assessment placement, tutorial directive cards).

Style validation (Feature 4) needs a fixture matrix: every built-in style × valid + invalid example curricula.

### Documentation

README sections to add or update:

- Schema reference: meta blocks, generalized assessments, style field.
- Authoring conventions: hook tagline length, role enum (per built-in style), image_prompt voice.
- Tutorial scaffold: directive syntax with examples.
- Built-in styles: when to use which.
- Migration: how to convert `pre_assessment` / `post_assessment` to the `assessments` array (one paragraph + a script if it's worth automating).

---

## Open Questions

1. **`role` enum vs open string at base-schema level.** I recommended open string with style-level constraint. Alternative: a base enum with style-level extension. Open-string is simpler; enum is more discoverable in IDE tooling. *Lean: open string.*

2. **Tutorial scaffold as directives vs new content block type.** I recommended directives (in markdown). A `type: tutorial` content block with a structured ref would enforce the pattern more strictly. *Lean: directives* — they preserve the markdown body as one file and avoid a parallel scaffold-spec format.

3. **Style file location for custom styles.** Currently I have it as a relative path in `style:`. Alternative: a `styles/` directory next to the curriculum YAML, discovered automatically. *Lean: explicit path* — more obvious to readers.

4. **Should `meta.duration_minutes` flow into a curriculum-wide time estimate?** Trivial to compute and surface on the curriculum index page. Worth doing in Feature 1 or as a follow-on. *Lean: do it in Feature 1, it's cheap.*

5. **Image generation pipeline for `hook.image_prompt`.** Out of scope for this plan, but worth noting that Feature 1's `image_prompt` field is the necessary precondition for a future `learningfoundry generate-images` command.

6. **Backward-compat aliasing horizon.** Deprecation warnings for `pre_assessment` / `post_assessment` start at v1.1. Drop entirely at v2.0? *Lean: yes, but no rush — keep them for at least 2 minor versions.*

---

## Suggested First Commit

Smallest meaningful slice that unblocks the CNN curriculum prompt:

1. Add `LessonMeta` and `ModuleMeta` Pydantic models.
2. Wire them as optional fields on `Lesson` and `Module`.
3. Pass-through to `curriculum.json`.
4. Add a single SvelteKit slice: render `meta.hook.tagline` at the top of the lesson body when present.
5. Tests: schema acceptance, JSON output contains meta, smoke test confirms tagline renders.

That's the v1.1.0-alpha.1 cut. The CNN curriculum can start authoring against it immediately. Everything else (tutorial scaffold, generalized assessments, styles) follows on its own cadence.
