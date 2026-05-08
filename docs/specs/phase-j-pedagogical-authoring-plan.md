# Phase J — Pedagogical Authoring (Plan)

Phase J adds first-class pedagogical authoring affordances to the learningfoundry curriculum schema and SvelteKit renderer. The phase is driven by friction surfaced while building the CNN curriculum prompt: structured pedagogical metadata, tutorial scaffolding, and the three-assessment pedagogy (pre / practice / post) currently have nowhere to live in the schema and have to be smuggled in via HTML comments and prose conventions.

This plan formalizes [phase-j-improvement-idea.md](phase-j-improvement-idea.md) (directional only — version numbers and "deprecated alias" framing in that doc are *not* authoritative; this plan is). Phase J ships three features pre-1.0 with no backward-compatibility shims; the fourth feature (configurable curriculum-style templates) is deferred to `## Future` because it depends on Features 1–3 having stabilized.

---

## Gap Analysis

### What exists today (post-Phase I, v0.63.0)

- `CurriculumV1` / `Module` / `Lesson` schema in [schema_v1.py](../../src/learningfoundry/schema_v1.py) supports content blocks (`text`, `video`, `quiz`, `exercise`, `visualization`).
- `Module` has exactly two assessment slots: `pre_assessment` and `post_assessment` (each an `AssessmentRef`). No third position; no positional flexibility.
- Lessons and modules carry only `id`, `title`, `description` and content. Nothing pedagogical (no `role`, `hook`, `objectives`, `introduces`, `duration_minutes`).
- The SvelteKit template renders content blocks straight through — no role chips, no hook taglines, no aggregate time estimates, no tutorial-scaffold styling.
- The CNN curriculum draft works around all of this by encoding pedagogical metadata in HTML comments, fenced code blocks, and prose conventions. None of it survives into `curriculum.json` and none of it is rendered.

### What's needed

1. A typed `meta` field at module and lesson level that captures pedagogical metadata, with `extra = "allow"` for author-defined fields.
2. A first-class tutorial-scaffold pattern (worked → faded → independent) recognized in markdown so it can be rendered consistently and validated.
3. A generalized `assessments` array that subsumes pre/practice/post and supports positional placement (before lessons / after lessons / before-or-after a specific lesson).
4. Frontend rendering for each of the above so authored metadata is not write-only.

---

## Feature Requirements

### J-F1. Lesson + Module Meta Blocks

**Functional**

- `Module.meta` (optional `ModuleMeta`): `theme`, `big_problem`, `objectives` (list), `experiential_summary`, `target_audience`. `extra = "allow"`.
- `Lesson.meta` (optional `LessonMeta`): `role` (open string), `hook` (optional `Hook` with `tagline` + `image_prompt`), `introduces` (list of strings — learning items new this lesson; concepts, equations, processes, methods, diagrams, patterns, etc.), `reinforces` (list of strings — items revisited from earlier lessons), `duration_minutes` (int). `extra = "allow"`.
- `meta` flows through `parser` → `pipeline` → `generator.py` into `curriculum.json` verbatim.
- Curriculum-wide time estimate aggregates `lesson.meta.duration_minutes` across all lessons; surfaced on the curriculum index page (Open Question #4 from the idea doc — confirmed in scope).

**Frontend**

- Lesson sidebar / breadcrumb shows a small chip for `meta.role` when present.
- Lesson body top renders `meta.hook.tagline` as a teaser.
- Curriculum index page shows aggregate time estimate when at least one lesson has `duration_minutes`.

**Non-goals for J-F1**

- No image-generation pipeline. `hook.image_prompt` is metadata only — read but not consumed.
- No `learningfoundry audit` for `introduces` / `reinforces` coverage. Stored but not validated.

### J-F2. Tutorial Scaffold via Markdown Directives

**Functional**

- The SvelteKit markdown renderer recognizes three container directives: `::: worked-example`, `::: faded-example`, `::: independent-practice`.
- Each directive renders with distinct visual treatment: worked = filled card; faded = outlined card with reduced contrast; independent = challenge prompt.
- Directives nest inside any `text` content block — no new content-block type is introduced.

**Validation**

- Parser-side lint (best-effort) flags malformed or unbalanced directives at curriculum-validation time. Exact mechanism left to implementation; minimum bar is a clear error message naming the lesson and an approximate location.

**Non-goals for J-F2**

- No `tutorial` content-block type (rejected — directives keep the lesson body as one file).
- No interactive features (progressive reveal, hint toggles). Static styling only.

### J-F3. Generalized `assessments` Array

**Functional**

- `Module.assessments: list[AssessmentDefinition]` where each entry has:
  - `role: str` (open string; conventional values: `pre`, `practice`, `post`, `checkpoint`)
  - `position`: one of `before_lessons`, `after_lessons`, `{ before_lesson: <lesson-id> }`, `{ after_lesson: <lesson-id> }`
  - `source`, `ref` (carry over from `AssessmentRef`)
  - `pass_threshold: float | None`
- `Module.pre_assessment` and `Module.post_assessment` are **removed** — no aliases, no deprecation warnings, no shim. Existing curricula migrate by hand or by a one-shot script (see Suggested First Stories).
- Parser resolves positional refs against the module's `lessons` array and errors on unknown lesson IDs.
- Pipeline / generator emit assessments into `curriculum.json` in resolved order; the SvelteKit module flow renders them at their resolved positions.

**Non-goals for J-F3**

- No mid-lesson assessment placement. `before_lesson` / `after_lesson` are the only positional grammar; intra-lesson injection is out of scope.
- No per-role gating semantics (e.g., "post must be passed to advance"). `pass_threshold` is recorded but enforcement is a future concern.

---

## Technical Changes

### New / modified Pydantic models — [schema_v1.py](../../src/learningfoundry/schema_v1.py)

- **New** `Hook(StrictModel)`: `tagline`, `image_prompt: str | None`. `model_config = ConfigDict(extra="allow")`.
- **New** `LessonMeta(StrictModel)`: `role`, `hook`, `introduces`, `reinforces`, `duration_minutes`. `extra = "allow"`.
- **New** `ModuleMeta(StrictModel)`: `theme`, `big_problem`, `objectives`, `experiential_summary`, `target_audience`. `extra = "allow"`.
- **New** `AssessmentPosition` discriminated union: `Literal["before_lessons", "after_lessons"]` | `BeforeLesson(lesson_id: str)` | `AfterLesson(lesson_id: str)`.
- **New** `AssessmentDefinition(StrictModel)`: `role`, `position: AssessmentPosition`, `source`, `ref`, `pass_threshold`.
- **Modified** `Lesson`: add `meta: LessonMeta | None = None`.
- **Modified** `Module`: add `meta: ModuleMeta | None = None`; add `assessments: list[AssessmentDefinition] = []`; **remove** `pre_assessment` and `post_assessment`.

### Parser — [parser.py](../../src/learningfoundry/parser.py)

- Resolve `AssessmentDefinition.position` references against `Module.lessons`; raise on unknown `lesson_id`.
- Order assessments deterministically: `before_lessons` first, then any `before_lesson:<id>` interleaved with lesson order, then `after_lesson:<id>`, then `after_lessons`.
- Lint pass for malformed `::: worked-example` / `faded-example` / `independent-practice` directive blocks inside `text` content (J-F2 validation).

### Pipeline / generator — [pipeline.py](../../src/learningfoundry/pipeline.py), [generator.py](../../src/learningfoundry/generator.py)

- Emit `meta` (module + lesson) into `curriculum.json` verbatim.
- Emit resolved-order `assessments` array into `curriculum.json` (replacing the old two-slot pre/post layout).
- Compute curriculum-wide aggregate `total_duration_minutes` from `lesson.meta.duration_minutes` (skip lessons missing the field; result is `None` if every lesson is missing it).

### SvelteKit template — [src/learningfoundry/sveltekit_template/](../../src/learningfoundry/sveltekit_template/)

- New TypeScript interfaces matching `LessonMeta`, `ModuleMeta`, `Hook`, `AssessmentDefinition`, `AssessmentPosition` in `lib/types/index.ts`.
- Sidebar / breadcrumb: render `meta.role` chip.
- Lesson body: render `meta.hook.tagline` teaser at the top when present.
- Curriculum index page: render aggregate time estimate when available.
- Markdown renderer: register container-directive plugin (`markdown-it-container` or equivalent for the existing markdown toolchain). Implement CSS for the three directive types.
- Module flow: render assessments at their resolved positions in the lesson list.

### Dependencies

- Frontend: a markdown container-directive plugin compatible with the existing renderer (exact pin chosen at implementation time; default candidate is `markdown-it-container` if the toolchain is markdown-it, or the `remark` equivalent if the toolchain is mdsvex / remark).
- No new Python dependencies.

### Hidden coupling — TypeScript ↔ Python contracts

Per existing project-essentials convention ("TypeScript interfaces ↔ Python dict schemas"), the new `LessonMeta`, `ModuleMeta`, `AssessmentDefinition`, `AssessmentPosition` types must stay in sync between [schema_v1.py](../../src/learningfoundry/schema_v1.py) and `lib/types/index.ts`. Phase J does not introduce a generator for these — they remain hand-maintained twins.

---

## Out of Scope

Walked with the developer; each item below is genuinely deferrable, not something hiding from this phase:

1. **Configurable curriculum-style templates** (Feature 4 from the idea doc). Adds a `style` field to the curriculum and per-style validation rules. Deferred to `## Future` because it materially depends on Features 1–3 having stabilized. Confirmed during planning.

2. **`learningfoundry generate-images` pipeline.** A future command that walks every `lesson.meta.hook.image_prompt`, runs each through an image API, and writes the result back. Phase J only stores the prompt; no consumer.

3. **`learningfoundry audit` for `introduces` / `reinforces` coverage.** A future command that flags items introduced but never reinforced (or vice versa: items reinforced that were never introduced anywhere upstream). Phase J stores the lists; auditing is a follow-on.

4. **Mid-lesson assessment placement.** The `before_lesson` / `after_lesson` grammar covers all three pedagogically interesting positions today (pre, practice landing before the hands-on lesson, post). Intra-lesson injection deferred until there's a concrete need.

5. **Per-role gating semantics.** `pass_threshold` is recorded but not enforced. Gating ("must pass post-assessment to advance") is a future concern that may also touch the progress-DB schema.

6. **Tutorial-scaffold interactivity** (progressive reveal, hint toggles, checkmark affordances). J-F2 ships static styling only.

7. **`tutorial` content-block type.** Considered and rejected: container directives keep the lesson body in one markdown file and avoid a parallel scaffold-spec format.

8. **Auto-discovery of style files.** Considered and rejected (alongside Feature 4 deferral): explicit path is more obvious to readers when style templates do land.

9. **Migration script for existing curricula** that use `pre_assessment` / `post_assessment`. Per the developer's instruction, breaking changes are acceptable in this phase — author-side migration is a manual edit. If it turns out painful in practice, a one-shot helper can be added as a follow-on patch.

---

## Suggested First Stories

The phase is not a single landable unit. Recommended story breakdown (final letters assigned at the stories step):

- **J.a — `Hook`, `LessonMeta`, `ModuleMeta` Pydantic models + JSON pass-through.** Schema-only slice; no rendering yet. Unblocks the CNN curriculum prompt to start authoring against the new shape.
- **J.b — Lesson role chip + hook tagline rendering** in SvelteKit. Smallest meaningful frontend slice so meta isn't write-only.
- **J.c — Curriculum-wide aggregate time estimate.** Reads `lesson.meta.duration_minutes`; surfaces on the index page. Cheap follow-on to J.a/b.
- **J.d — Markdown container-directive plugin + worked/faded/independent CSS.** J-F2 in one slice; parser-side directive lint included.
- **J.e — `AssessmentDefinition` model + parser positional resolution.** J-F3 schema slice; replaces `pre_assessment` / `post_assessment` outright.
- **J.f — SvelteKit module-flow renders assessments at resolved positions.** J-F3 frontend slice.
- **J.g — Tests + docs sweep.** Schema acceptance, generator output, smoke tests; README updates for meta blocks, directive syntax, and the assessments array.

A spike story is not required — the phase introduces no new integration boundaries (no new external dependencies on the Python side, and the frontend directive plugin is well-trodden territory).

---

## Cross-Cutting Concerns

### Frontend / backend lockstep

Each schema change should land with its SvelteKit slice in the same release-window so curricula authored against the new shape actually look different in the rendered app. Otherwise meta is a write-only graveyard while the frontend lags.

### Tests

Per project-essentials Testing conventions, Phase J adds:

- **Schema acceptance**: each new model parses valid inputs and rejects invalid ones with useful messages.
- **Generator output**: `curriculum.json` contains `meta`, the resolved `assessments` array, and the aggregate time estimate when applicable.
- **Parser**: positional resolution succeeds for valid `before_lesson` / `after_lesson` IDs and errors clearly on unknown IDs.
- **Smoke tests**: rendered SvelteKit app contains role chips, hook taglines, directive cards, and assessments at the expected positions in module flow.

### Documentation

README / docs updates accompany J.g:

- Schema reference: meta blocks, generalized assessments.
- Authoring conventions: hook tagline, role values used by the team, image_prompt voice.
- Tutorial scaffold directive syntax with examples.
- Migration note for any in-tree curricula that used `pre_assessment` / `post_assessment`.

---

## Open Questions Carried Forward

The idea doc raised these; resolved status for the plan:

1. **`role` enum vs open string.** Resolved: open string at base-schema level. (Style-level constraint deferred with Feature 4.)
2. **Tutorial scaffold as directives vs new content-block type.** Resolved: directives.
3. **Style file location for custom styles.** N/A — Feature 4 deferred.
4. **`meta.duration_minutes` aggregation.** Resolved: in scope for J-F1, surfaced on the curriculum index.
5. **Image generation pipeline.** Out of scope (item 2 above).
6. **Backward-compat aliasing horizon.** N/A — no aliases this phase per developer instruction.
