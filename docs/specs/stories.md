# stories.md -- learningfoundry (python)

This document breaks the `learningfoundry` project into an ordered sequence of small, independently completable stories grouped into phases. Each story has a checklist of concrete tasks. Stories are organized by phase and reference modules defined in `tech-spec.md`.

Put **`vX.Y.Z` in the story title only when that story ships the package version bump** for that release. Doc-only or polish stories **omit the version from the title** (they share the release with the preceding code story, or use your project’s doc-release policy). **One semver bump per owning story** — extra tasks on the *same* story share that bump; see `project-essentials.md`. Semantic versioning applies to the package. Stories are marked with `[Planned]` initially and changed to `[Done]` when completed.

For a high-level concept (why), see [`concept.md`](concept.md). For requirements and behavior (what), see [`features.md`](features.md). For implementation details (how), see [`tech-spec.md`](tech-spec.md). For project-specific must-know facts, see [`project-essentials.md`](project-essentials.md) (`plan_phase` appends new facts per phase). For the workflow steps tailored to the current mode (cycle steps, approval gates, conventions), see [`docs/project-guide/go.md`](../project-guide/go.md) — re-read it whenever the mode changes or after context compaction.

---

## Version Cadence

Standard semantic versioning, with these conventions:

- **Every story belongs to a phase.** Bugfix stories included. No orphan stories.
- **Per-story bumping** (when a story owns its own release):
  - Bugfix or trivial change → **patch** (`vX.Y.Z+1`)
  - Feature or improvement → **minor** (`vX.Y+1.0`)
  - Breaking change → **major** (`vX+1.0.0`). Post-1.0 only, and only via the `plan_production_phase` mode, which negotiates with the developer about whether the breakage is substantively user-facing or technically-but-trivially breaking (example: a log-format change is technically breaking, but if logs aren't a core consumer capability, the developer may judge it minor or even patch).
- **Phase-bundling option:** a phase can run unversioned during work and ship a single release/tag at end-of-phase. Stories within the phase carry no version in their title; the phase's last story owns the bump (magnitude determined by the highest-impact change in the bundle).
- **No out-of-order implementation.** Story order in this file is the order of execution. If work order needs to change, **reorganize/renumber here first** — don't skip ahead and create version-number gaps.
- **Pre-1.0:** standard semver applies; version starts at `v0.1.0` (Story A.a).
- **Post-1.0:** every phase must go through `plan_production_phase` (the lighter `plan_phase` is pre-1.0 only). Major bumps only happen through that mode's negotiation step.

This is the authoritative cadence rule. **Do not extrapolate the bump magnitude from `pyproject.toml`'s current version** — re-read this section whenever you're about to assign a version to a story.

---



## Phase J: Pedagogical Authoring

Phase J adds first-class pedagogical authoring affordances to the curriculum schema and SvelteKit renderer. Driven by friction surfaced while building the CNN curriculum prompt: structured pedagogical metadata, tutorial scaffolding, and the three-assessment pedagogy (pre / practice / post) currently have nowhere to live in the schema and have to be smuggled in via HTML comments and prose conventions. See [phase-j-pedagogical-authoring-plan.md](phase-j-pedagogical-authoring-plan.md) for the full plan; this section breaks the work into landable stories.

Phase J includes Features 1–3 from the source idea doc. Feature 4 (configurable curriculum-style templates) is deferred to `## Future` because it depends on Features 1–3 having stabilized.

Phase J is **pre-1.0**, planned via the `plan_phase` mode. No backward-compatibility shims: `pre_assessment` / `post_assessment` are removed outright in Story J.e (replaced by the generalized `assessments` array).

### Story J.a: v0.64.0 — Lesson and Module 'meta' Pydantic Models + JSON Pass-Through [Done]

learningfoundry's curriculum schema has no place for pedagogical metadata. Authors who want to declare a lesson's `role` (opener, concept, story, math, tutorial, practice, hands_on, bonus), an opening `hook` with a tagline, the learning items the lesson `introduces` and `reinforces`, an estimated `duration_minutes`, or module-level `objectives` and a `theme` have to smuggle that into HTML comments and fenced code blocks — invisible to the build pipeline.

Story J.a adds the schema slice: `LessonMeta`, `ModuleMeta`, and `Hook` Pydantic models, attached as optional fields on `Lesson` and `Module`, passed through to `curriculum.json` verbatim. No frontend rendering yet (that's J.b–J.c). This is the smallest landable cut that unblocks the CNN curriculum prompt to start authoring against the v0.64.0 shape.

`extra = "allow"` on each meta model so authors can attach their own fields without schema churn.

**Schema:**
```yaml
modules:
  - id: mod-01
    title: "Why convolutions exist"
    meta:
      theme: "Why convolutions exist"
      big_problem: "Fully-connected networks ignore image structure."
      objectives: ["Explain why FC nets fail on images", "Describe weight sharing"]
      experiential_summary: "Build your first conv layer in PyTorch."
      target_audience: "Intermediate Python; high-school math"

    lessons:
      - id: lesson-01
        title: "..."
        meta:
          role: opener
          hook:
            tagline: "What if your first layer of vision was just a flashlight on the world?"
            image_prompt: "A 1960s neuroscience lab; oscilloscope tracing a single spike."
          introduces: [receptive_field, simple_cells]
          reinforces: []
          duration_minutes: 15
        content_blocks: [...]
```

**Out of scope (this story):** any frontend rendering; aggregate time estimate (J.c); audit/lint of `introduces` / `reinforces` coverage; image generation from `hook.image_prompt`.

**Tasks:**

- [x] `src/learningfoundry/schema_v1.py`:
  - [x] Add `Hook(StrictModel)`: `tagline: str`, `image_prompt: str | None`. `model_config = ConfigDict(extra="allow")`.
  - [x] Add `LessonMeta(StrictModel)`: `role: str | None`, `hook: Hook | None`, `introduces: list[str] = []`, `reinforces: list[str] = []`, `duration_minutes: int | None`. `extra = "allow"`.
  - [x] Add `ModuleMeta(StrictModel)`: `theme: str | None`, `big_problem: str | None`, `objectives: list[str] = []`, `experiential_summary: str | None`, `target_audience: str | None`. `extra = "allow"`.
  - [x] Add `meta: LessonMeta | None = None` to `Lesson`.
  - [x] Add `meta: ModuleMeta | None = None` to `Module`.
- [x] `src/learningfoundry/resolver.py` and `pipeline.py`: ensure `meta` propagates from parsed YAML into the resolved curriculum without modification.
- [x] `src/learningfoundry/generator.py`: emit `lesson.meta` and `module.meta` into `curriculum.json` verbatim.
- [x] `src/learningfoundry/sveltekit_template/src/lib/types/index.ts`: add `LessonMeta`, `ModuleMeta`, `Hook` interfaces matching the Pydantic shape.
- [x] `tests/test_schema_v1.py`: each new model parses valid input and rejects invalid input with useful messages; `extra = "allow"` accepts unknown keys.
- [x] `tests/test_generator.py`: a curriculum with `meta` produces `curriculum.json` containing the meta blocks; a curriculum without `meta` produces JSON with `meta: null`.
- [x] `docs/specs/features.md`: new "Pedagogical metadata" subsection under FR-2 (Content Resolution), describing `meta` on lesson and module.
- [x] `docs/specs/tech-spec.md`: extend the `schema_v1.py` data-models section with `Hook`, `LessonMeta`, `ModuleMeta`.
- [x] Bump version to v0.64.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] Update `CHANGELOG.md` with a v0.64.0 Added entry.
- [x] Verify: `pyve test` passes, `ruff` and `mypy` clean.

---

### Story J.b: v0.65.0 — Lesson Role Chip and Hook Tagline Rendering [Done]

J.a stored `meta` but rendered nothing. Story J.b adds the two highest-leverage frontend slices so meta isn't write-only:
- A small chip in the lesson sidebar / breadcrumb shows `meta.role` when present.
- The lesson body top renders `meta.hook.tagline` as a teaser line above the first content block.

Both render only when their respective fields are present — no defaults, no placeholders. Styling matches the existing component vocabulary (the role chip parallels existing status indicators; the tagline reads as a quiet superscript above the lesson title).

**Out of scope:** rendering `hook.image_prompt` (no consumer exists pre image-generation pipeline); module-level `meta.theme` rendering on the module index (revisit if useful after CNN authoring).

**Tasks:**

- [x] `src/learningfoundry/sveltekit_template/`: identify the lesson-sidebar / breadcrumb component and add a role chip rendering when `lesson.meta?.role` is set. (Sidebar = `LessonList.svelte`.)
- [x] `src/learningfoundry/sveltekit_template/`: identify the lesson-body shell and add tagline rendering above the first content block when `lesson.meta?.hook?.tagline` is set. (Body shell = `LessonView.svelte`; tagline lives above the `<h1>` lesson title.)
- [x] CSS for the chip (small, neutral, distinct from progress/lock indicators) and tagline (italic, muted, single line).
- [x] Component tests under the existing vitest setup: chip renders with role text, hides without; tagline renders with text, hides without.
- [x] Smoke test extension: fixture `valid-curriculum.yml` carries role + tagline + module meta; `test_pedagogical_meta_survives_build` pins the data-contract end-to-end on the production `build/curriculum.json`. (DOM rendering covered by vitest; SvelteKit app is `ssr=false`, so the prerendered HTML can't carry the values pre-hydration.)
- [x] `docs/specs/features.md`: add to the SvelteKit-output section a one-paragraph note on how `meta.role` and `meta.hook.tagline` surface in the UI.
- [x] Bump version to v0.65.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] Update `CHANGELOG.md`.
- [x] Verify: `pyve test`, vitest, smoke build.

---

### Story J.c: v0.66.0 — Curriculum-Wide Aggregate Time Estimate [Done]

Cheap follow-on to J.a/b that converts `lesson.meta.duration_minutes` (singular per-lesson author estimates) into a curriculum-wide signal: the dashboard / index page shows total estimated duration when at least one lesson has the field set.

Aggregate is computed at generation time, written into `curriculum.json` as `total_duration_minutes: int | null` (null when no lesson has the field). Frontend reads the precomputed value rather than walking lessons at render time.

**Out of scope:** per-module aggregation (would surface on each module's header — revisit if useful); learner-elapsed-time display (different domain — that's progress data); adaptive estimates based on past learner pace.

**Tasks:**

- [x] `src/learningfoundry/generator.py`: compute `sum(lesson.meta.duration_minutes for lesson in all_lessons if lesson.meta and lesson.meta.duration_minutes)`; emit `total_duration_minutes` at the curriculum top level. `null` when the sum has no contributors.
- [x] `src/learningfoundry/sveltekit_template/`: index page (`+page.svelte`) reads `curriculum.total_duration_minutes` and renders "≈ Xh Ym" (or "≈ Xm" under an hour, "≈ Xh" for whole hours) when non-null. Format helper lives at `lib/utils/duration.ts` so the rendering branch is one-line.
- [x] `tests/test_generator.py`: aggregate computed correctly with mixed (some-set, some-null) lessons; absent when no lesson contributes; absent when `meta` is set but `duration_minutes` is unset.
- [x] Component / smoke test: helper covered by `lib/utils/duration.test.ts` (every format branch + null/zero/negative); smoke test pins `total_duration_minutes == 15` against the production build.
- [x] `docs/specs/features.md`: note the aggregate behaviour under FR-3.
- [x] Bump version to v0.66.0.
- [x] Update `CHANGELOG.md`.
- [x] Verify: `pyve test`, vitest, smoke build.

---

### Story J.d.1: v0.67.0 — Tutorial Scaffold Directives — Plugin + Rendering + CSS [Done]

The worked → faded → independent practice pattern is high-leverage in technical curricula but currently survives only as a prose convention. Story J.d recognizes it in markdown using container directives (already common in MkDocs / MDX / mdsvex / remark toolchains):

```markdown
::: worked-example
Compute output shape for a 32×32 input, 3×3 kernel, stride 1, padding 0.
We apply (W − K + 2P) / S + 1 = 30. Output: 30×30.
:::

::: faded-example
For a 64×64 input, 5×5 kernel, stride 1, padding 2 — what's the output shape?
:::

::: independent-practice
Given 28×28 input, design a Conv2d that outputs 14×14. State your kernel, stride, padding.
:::
```

J.d.1 wires a compatible container-directive plugin into the SvelteKit markdown renderer and styles the three directive names: `worked-example` = filled card; `faded-example` = outlined card with reduced contrast; `independent-practice` = challenge prompt. No new content-block type; directives nest inside any `text` block's markdown.

J.d.1 ships the user-visible feature for authors who write valid markdown. The Python-side lint that turns malformed `:::` blocks into a loud build-time error lands separately in **J.d.2** so the rendering work has a tight blast radius.

**Out of scope (this story and J.d.2):** interactivity (progressive reveal, hint toggles, checkmark affordances) — static styling only; new directive names beyond the three above (revisit if real curricula need more).

**Tasks:**

- [x] `src/learningfoundry/sveltekit_template/`: markdown toolchain is `marked`; added a custom `marked` extension at `lib/utils/markdown-directives.ts` (no new dependency) and registered it in `markdown.ts`.
- [x] CSS for the three directive types added to `src/app.css` as plain CSS classes (`.lf-directive`, `.lf-directive-worked-example`, `.lf-directive-faded-example`, `.lf-directive-independent-practice`).
- [x] Component / smoke test: `markdown.test.ts` exercises all three wrappers + nested markdown + back-to-back blocks + unknown-name pass-through + fenced-code-block isolation. Fixture `content/mod-01/lesson-01.md` carries all three directives; `test_tutorial_directives_survive_in_markdown_source` and `test_directive_styles_in_bundled_css` pin the source + CSS through the production build.
- [x] `docs/specs/features.md`: new "Tutorial scaffold directives" subsection under FR-3.
- [x] `README.md`: author-facing example of all three directives + Table-of-Contents entry.
- [x] Bump version to v0.67.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] Update `CHANGELOG.md` with a v0.67.0 Added entry; J.d.2 follow-up flagged.
- [x] Verify: `pyve test`, vitest, smoke build.

---

### Story J.d.2: v0.67.1 — Tutorial Scaffold Directives — Python Lint Pass [Done]

J.d.1 makes the three directives render. J.d.2 closes the gap on malformed `:::` blocks by adding a best-effort lint pass at curriculum-validation time so authors get a clear build-time error naming the lesson and approximate location, rather than discovering the problem at render time (where the markdown plugin's recovery behaviour is the only signal).

Defensive developer-experience hardening on top of an already-working feature — landed as a patch bump.

**Tasks:**

- [x] New `src/learningfoundry/directives.py` (cleaner than co-locating in `parser.py` since the lint runs at content-resolution time, not YAML-parse time): `lint_directives(markdown, location)` scans for the three known directive opens with matching `:::` closes; hooked into `resolver._resolve_text` after the markdown is read.
- [x] New `tests/test_directives.py`: balanced (single, all three names, back-to-back, blank-lines-inside) parses cleanly; unbalanced (open with no close, two opens with one close) raises with lesson location + line number; unknown directive names (`::: tip`) pass through; fenced code blocks (``` and ~~~) ignore directive-shaped lines.
- [x] `docs/specs/tech-spec.md`: new `directives.py` subsection documenting the lint contract, the resolver hook point, and the TS↔Python `KNOWN_DIRECTIVES` coupling. The resolver subsection's text-block bullet now mentions the lint step.
- [x] Bump version to v0.67.1 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] Update `CHANGELOG.md` with a v0.67.1 Added entry.
- [x] Verify: `pyve test`, `ruff`, `mypy`.

---

### Story J.e: v0.68.0 — Generalized 'assessments' Array [Done]

Today's two-slot `pre_assessment` / `post_assessment` covers the priming and recap positions but cannot represent practice quizzes (the third pedagogically interesting position, typically landing before the hands-on lesson). Story J.e replaces both fields with a single generalized `assessments: list[AssessmentDefinition]` array on `Module`, supporting positional placement.

**Schema:**
```yaml
modules:
  - id: mod-01
    title: "..."
    assessments:
      - role: pre
        position: before_lessons
        source: quizazz
        ref: assessments/mod-01-pre.yml

      - role: practice
        position: { before_lesson: lesson-07 }
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

`role` is an open string (conventional values: `pre`, `practice`, `post`, `checkpoint`). `position` is a discriminated union: `Literal["before_lessons", "after_lessons"]`, or `{ before_lesson: <lesson-id> }`, or `{ after_lesson: <lesson-id> }`. Parser resolves positional refs against the module's `lessons` and errors on unknown lesson IDs. Pipeline / generator emit assessments in resolved order into `curriculum.json` (stripping the position metadata; the order *is* the placement signal for downstream consumers).

**Breaking change:** `Module.pre_assessment` and `Module.post_assessment` are removed. No alias, no deprecation warning, no shim. In-tree fixtures and the in-progress CNN curriculum migrate by hand. Pre-1.0 makes this acceptable per the Version Cadence rules.

**Out of scope:** mid-lesson assessment placement (intra-lesson injection deferred); per-role gating semantics (`pass_threshold` recorded but not enforced — gating is a future concern that may also touch the progress-DB schema); SvelteKit module-flow rendering of assessments at resolved positions (that's J.f).

**Tasks:**

- [x] `src/learningfoundry/schema_v1.py`: added `BeforeLesson`, `AfterLesson`, `AssessmentPosition` (Pydantic 2 smart-union), `AssessmentDefinition`. `Module.pre_assessment` / `Module.post_assessment` removed; `Module.assessments: list[AssessmentDefinition] = []` added with a `model_validator` that rejects unknown lesson refs.
- [x] Lesson-id validation lives on `Module` (not `parser.py`) so `model_validate` catches typos at parse time. Canonical placement order is computed in `resolver._resolve_assessments` (cleaner home than the parser since the resolver already owns content-resolution); the order is materialized onto `ResolvedModule.assessments` so the generator does not recompute.
- [x] `src/learningfoundry/resolver.py` / `generator.py`: emit the resolved `assessments` array in computed order into `curriculum.json`. `pre_assessment` / `post_assessment` are gone from the JSON shape (regression-tested in `TestAssessmentsArrayInCurriculumJson.test_old_pre_post_fields_absent`).
- [x] `src/learningfoundry/sveltekit_template/src/lib/types/index.ts`: new `AssessmentDefinition` and `AssessmentPosition` types; `Module` drops the two old fields and gains `assessments`.
- [x] Fixtures migrated: `tests/fixtures/valid-curriculum.yml` → `assessments[]`; `sveltekit_template/e2e/fixtures/curriculum.json` → `assessments: []`. ProgressDashboard's two pre/post score rows removed (per-learner score UI now bare; rebuild on the new shape lands in J.f).
- [x] `tests/test_schema_v1.py` `TestAssessmentDefinition`: 11 cases pinning each `position` form, `pass_threshold` validation, unknown lesson-ref rejection, invalid position string rejection, `assessments` default empty, extra-field rejection, and legacy `pre_assessment` field rejection.
- [x] `tests/test_resolver.py` `TestAssessmentResolution`: 6 cases pinning before/after-lessons resolution, lesson-anchored interleaving order, JSON-friendly position serialization, content-resolution-error wrapping, and empty-assessments default.
- [x] `tests/test_generator.py` `TestAssessmentsArrayInCurriculumJson`: 5 cases pinning order preservation, position serialization shape, `pass_threshold` pass-through, `content` pass-through, and absence of legacy fields.
- [x] `docs/specs/features.md`: new "Module assessments — generalized array" subsection with the position grammar; FR-5 narrative updated.
- [x] `docs/specs/tech-spec.md`: `BeforeLesson` / `AfterLesson` / `AssessmentPosition` / `AssessmentDefinition` documented; `Module` Pydantic class updated; `ResolvedAssessment` dataclass added; `curriculum.json` example shows the new shape; TypeScript `Module` interface updated.
- [x] `docs/specs/quizazz/dependency-spec.md` had no references to the old field names; no edit needed.
- [x] `README.md`: curriculum-YAML example shows pre / practice / post entries with each position form.
- [x] Bumped version to v0.68.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] Updated `CHANGELOG.md` — `Removed (BREAKING)` section flags the field removal prominently.
- [x] Verify: `pyve test` 324 passed, `pnpm test` 211 passed, `ruff` clean, `mypy` clean. Smoke build (pnpm install + vite build) intentionally not run in this turn — covered by CI.

---

### Story J.f: v0.69.0 — SvelteKit Module Flow Renders Assessments at Resolved Positions [Done]

J.e replaced `pre_assessment` / `post_assessment` with a resolved-order `assessments` array but the SvelteKit module-flow component still renders against the old two-slot model. Story J.f catches the frontend up: the module page reads `module.assessments` (in the order the generator emitted) and renders each entry at its position in the lesson list, with the role visible in the UI label.

`pass_threshold` is rendered as a secondary annotation on the assessment card ("70% to pass") when present, but enforcement remains out of scope (no gating).

**Out of scope:** gating ("must pass post to advance"); per-role styling beyond label text; mid-lesson assessment placement.

**Tasks:**

- [x] `src/learningfoundry/sveltekit_template/`: module-flow / lesson-list component is `LessonList.svelte` (rendered via `ModuleList.svelte`). Replaced no-op pre/post UI with iteration over a derived `flow` built by `interleaveModuleFlow(lessons, assessments)`.
- [x] Render each assessment at its resolved position; helper builds the flow by reading `position` once. Component does not re-resolve placement — it trusts the resolver-emitted order to disambiguate ties within each placement bucket.
- [x] Display assessment `role` capitalized as `<Role> Assessment` (helper `capitalizeRole`). Open-string roles are preserved verbatim after the first letter.
- [x] Display `pass_threshold` as `"X% to pass"` via `formatPassThreshold` helper; rendered only when threshold is set + within `(0, 1]`.
- [x] Component tests: 10 unit cases in `module-list.test.ts` (interleave correctness, helper formatting); 5 DOM cases in `LessonList.test.ts` (no-assessments, single-pre, all-three-interleaved, threshold present/absent).
- [x] `docs/specs/features.md`: new "Module flow renders assessments at resolved positions" subsection under FR-3.
- [x] Bumped version to v0.69.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] Updated `CHANGELOG.md`.
- [x] Verify: `pyve test` 324 passed, `pnpm test` 226 passed, `ruff` clean, `mypy` clean. Smoke build (pnpm install + vite build) intentionally not run in this turn — covered by CI.

---

### Story J.g: Phase J Close — Cross-Cutting Smoke + README Sweep [Done]

Final phase-close story that ties off the loose ends each per-feature story didn't pick up:

- A single end-to-end smoke fixture exercising every Phase J affordance simultaneously (lesson + module `meta`, all three tutorial directives, all three assessment roles with mixed positions, `duration_minutes` aggregation). Verifies the features compose cleanly.
- README narrative section "Pedagogical authoring" stitching together the per-feature docs into a single author-facing story with a worked example.
- A migration paragraph in README documenting how to convert `pre_assessment` / `post_assessment` to `assessments[]` for any external curriculum that pre-dates v0.68.0.

No version bump in the title — this story is doc + integration-test only and shares the v0.69.0 release with J.f.

**Out of scope:** new functional behaviour; refactor of any per-story implementation.

**Tasks:**

- [x] `tests/`: new fixture at `tests/fixtures/phase-j-curriculum.yml` + content at `tests/fixtures/phase-j-content/` exercising every affordance. New `tests/test_phase_j_smoke.py` (9 cases) asserts that `curriculum.json` carries module + lesson `meta`, all three directive opens, the three assessment roles in canonical resolved order with their position payloads, `pass_threshold` pass-through, content resolution, the `total_duration_minutes` aggregate, and the absence of legacy `pre_assessment` / `post_assessment` fields. DOM rendering of each affordance is covered by the per-feature vitest suites (markdown directives in `markdown.test.ts`, lesson tagline + role chip in `LessonView.test.ts` / `LessonList.test.ts`, assessment rows in `LessonList.test.ts`, total-duration formatting in `duration.test.ts`); the integration anchor here is the data contract.
- [x] `README.md`: replaced the standalone "Tutorial scaffold directives" section with a single "Pedagogical authoring" section that introduces meta + directives + assessments together, includes a worked example, and ends with a `pre_assessment` / `post_assessment` → `assessments[]` migration block. ToC entry updated.
- [x] `docs/specs/features.md`: brief "Phase J: Pedagogical authoring" header inserted before the per-feature subsections (J.a / J.b / J.c / J.d.1 / J.e / J.f) and pointing at the integration test.
- [x] No version bump (shares v0.69.0 with J.f). Phase J release ships at v0.69.0.
- [x] Verify: `pyve test`, vitest, `ruff`, `mypy`. Smoke build (pnpm install + vite build) intentionally not re-run in this turn — covered by CI.

---

### Story J.h: v0.69.1 — `CurriculumMeta` + Project-Specific `meta` Schema Extensions [Done]

Two combined additions, motivated by post-J authoring experience on LLM-driven curricula:

1. **New `CurriculumMeta` model** parallel to `LessonMeta` / `ModuleMeta`. Today `CurriculumDef` ([schema_v1.py:242](../../src/learningfoundry/schema_v1.py#L242)) has no `meta` field at all — curriculum-wide pedagogical context (target audience, objectives, prerequisites) has nowhere to live except prose in `description`. J.h adds an optional `meta: CurriculumMeta | None` field on `CurriculumDef`, with the same `extra="allow"` posture as the other meta models.

2. **Project-specific schema extensions** for all three meta models. `LessonMeta` and `ModuleMeta` ride on `extra="allow"` ([schema_v1.py:157,173](../../src/learningfoundry/schema_v1.py#L157)) — and the new `CurriculumMeta` will too — so authors can attach custom fields (`covers`, `difficulty`, `prerequisites`, …) without a learningfoundry schema change. The trade-off is that `extra="allow"` silently swallows *phantom* fields: an LLM that writes `prequisites` instead of `prerequisites`, or `cover` instead of `covers`, hits no error. Build succeeds, the field is lost in the resolved `curriculum.json`, and the bug surfaces (or doesn't) downstream. J.h adds an optional schema-extensions file that, when present, replaces `extra="allow"` with strict whitelist-reject validation over a project-declared set of additional fields per meta model. Without the file, today's behaviour is preserved exactly — opt-in, no migration for any existing curriculum.

**Declared fields for `CurriculumMeta`** (initial minimal set; extensions cover the rest): `target_audience: str | None`, `objectives: list[str]`, `prerequisites: list[str]`. Mirrors the opinionated-small-set + escape-hatch pattern of `ModuleMeta` ([schema_v1.py:166-179](../../src/learningfoundry/schema_v1.py#L166-L179)). Rendering of these is deferred to a later phase; today they pass through to `curriculum.json` for downstream tooling, exactly as `ModuleMeta` did when J.a landed.

**Extension file contract:** `learningfoundry-schema-extensions.yml` next to `curriculum.yml` (path overridable via `--schema-extensions PATH` and `[tool.learningfoundry] schema_extensions` in `pyproject.toml`). Declares additional fields for the three `extra="allow"` meta models. Illustrative shape:

```yaml
version: "1"
curriculum_meta:
  extra: forbid                                            # default when file present
  fields:
    pedagogical_approach: { type: str, required: false }
    estimated_total_minutes: { type: int, required: false }
module_meta:
  fields:
    curriculum_thread: { type: str, required: false }
lesson_meta:
  fields:
    covers:        { type: list[str], default: [] }
    difficulty:    { type: enum, values: [intro, intermediate, advanced] }
    prerequisites: { type: list[str], default: [] }
```

At parse time, `pydantic.create_model` synthesizes `_ExtendedCurriculumMeta` / `_ExtendedModuleMeta` / `_ExtendedLessonMeta` subclasses with the declared fields appended and `model_config = ConfigDict(extra="forbid")`. The parser swaps these in via the existing `CurriculumDef.meta` / `Module.meta` / `Lesson.meta` field types.

**Decision:** the declarative-file path (`create_model`) is chosen over a Python-subclass hook because the motivating use case is LLM-driven authoring — keeping the entire author surface in YAML lets the LLM extend the schema without switching modes. A Python-hook escape (`schema_module = "..."`) is recorded as a possible follow-up if a curriculum needs cross-field validators.

**Out of scope:** Python-module schema hook (deferred); extending the mechanism to `Hook` (small surface, defer until asked); extending to non-`extra="allow"` models (`Lesson`, `Module`, `CurriculumDef` itself stay strict unconditionally — only their `.meta` sub-blocks are extensible); declarative cross-field validators ("`difficulty: advanced` requires non-empty `prerequisites`"); SvelteKit rendering of `CurriculumMeta` fields (data pass-through only); SvelteKit-side type generation for extended fields (consumers read them as untyped JSON for now).

**Tasks:**

- [x] `src/learningfoundry/schema_v1.py`: new `CurriculumMeta(StrictModel)` with `model_config = ConfigDict(extra="allow")` and declared fields `target_audience: str | None = None`, `objectives: list[str] = Field(default_factory=list)`, `prerequisites: list[str] = Field(default_factory=list)`. Add `meta: CurriculumMeta | None = None` to `CurriculumDef`.
- [x] `src/learningfoundry/sveltekit_template/src/lib/types/index.ts`: mirror `CurriculumMeta` as a TS interface (optional `target_audience?: string`, `objectives?: string[]`, `prerequisites?: string[]`, plus `[key: string]: unknown` for extras) and add `meta?: CurriculumMeta` to the curriculum-level type. (Matches the hidden-coupling rule from project-essentials.)
- [x] New `src/learningfoundry/schema_extensions.py`: `SchemaExtensions` Pydantic model (strict-validated, so typos in the *extension* file also fail loudly) describing the file contract; `build_extended_meta_models(extensions: SchemaExtensions) -> tuple[type[CurriculumMeta], type[ModuleMeta], type[LessonMeta]]` using `pydantic.create_model`. Supported `type:` values: `str`, `int`, `bool`, `list[str]`, `enum` (requires `values:`). Per-field `required: bool` (default `true`) and `default:` (optional).
- [x] Wire into `parser.py` / `pipeline.py`: auto-discover `learningfoundry-schema-extensions.yml` next to the curriculum; honour `--schema-extensions PATH` if set. When found, build the extended models and dispatch parsing through them so `CurriculumDef.meta` / `Module.meta` / `Lesson.meta` validate against the extended subclasses. When absent, the base meta models are used unchanged.
- [x] CLI: new `--schema-extensions PATH` flag on `build`, `validate`, `preview`. Resolution order: CLI > `pyproject.toml [tool.learningfoundry] schema_extensions` > auto-discovery > none.
- [x] Error contract: unknown field at any `meta` level → Pydantic `ValidationError` naming the field (existing behaviour, now triggered by the synthesized `extra="forbid"`); malformed extension file → typed `SchemaExtensionError` citing the file path; unknown `type:` in extension file → typed error naming the field and listing supported types.
- [x] Tests `tests/test_schema_v1.py` additions (~4 cases): `CurriculumMeta` accepts the three declared fields with right types; `CurriculumMeta` rejects wrong types; `CurriculumDef.meta` is optional (omission validates); `extra="allow"` round-trip works on `CurriculumMeta`.
- [x] Tests `tests/test_schema_extensions.py` (~12 cases): no file present → today's `extra="allow"` behaviour intact for all three meta models (regression guard); file present declaring `lesson_meta.covers` → valid lesson with `covers` accepted, lesson with `covres` typo rejected with field name in error; `difficulty: enum` → valid value accepted, out-of-vocab rejected with allowed-values list in error; `required: true` without `default:` → omission rejected; per-model `extra: allow` override restores today's behaviour for that model only; extensions applied independently to `curriculum_meta` / `module_meta` / `lesson_meta` (typo in curriculum_meta rejected without affecting lesson_meta validation); malformed extension file rejected at load time; `--schema-extensions` CLI flag honoured; `pyproject.toml` resolution path honoured.
- [x] `docs/specs/features.md`: new "`CurriculumMeta`" subsection (mirrors the Module/Lesson meta subsections) and new "Project-specific `meta` schema extensions" subsection under FR-3 with the worked YAML example and the typo-rejection failure mode.
- [x] `README.md`: add `CurriculumMeta` documentation under "Pedagogical authoring → meta reference" (parallel to the existing Lesson/Module entries); extend the "Custom `meta` fields" subsection with a follow-on "Strict project-specific extensions" sub-subsection showing the extension file + the error message produced on a typo.
- [x] `docs/specs/tech-spec.md`: `CurriculumMeta` added to schema overview; new `schema_extensions.py` subsection documenting the file contract, the `create_model` integration point, the parser swap-in mechanism, and the file-path resolution order.
- [x] Bump version to v0.69.1 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] Update `CHANGELOG.md`.
- [x] Verify: `pyve test`, vitest, `ruff`, `mypy`.

---

### Story J.i: Quiz → Assessment Terminology Rename (Docs) [Done]

Streamline crufty terminology across the planning artifacts: `Quiz*` → `Assessment*` on every learningfoundry-owned surface, leaving the `quizazz` vendor name and its exports (`<QuizBlock>` component, `compile_quiz()` method, `QuizazzProvider` adapter class, `quizazz_builder` references that survive — none in our code) untouched. Motivated by the schema discriminator confusion: `type: quiz` was the YAML literal that gated a `QuizBlock` Pydantic model, while the conceptual category in features/tech-spec was already "assessment" — the inconsistency made every reader pause.

Decisions baked into this pass:
- **Pure rename, no scope broadening.** `Assessment` does not absorb `Exercise`; the two providers stay separate. Exercise blocks remain `type: exercise`.
- **YAML discriminator renamed** (`type: quiz` → `type: assessment`) alongside the Python/TS/SQL identifiers, accepting the curriculum-YAML breaking change (pre-1.0).
- **IndexedDB migration: data-loss.** The runtime SQLite schema rename (`quiz_scores` → `assessment_scores`, columns `quiz_ref`/`quiz_type` → `assessment_ref`/`assessment_type`) drops the old table and creates the new one fresh on next `Database.getDb()`. No row-copy migration.
- **Manifest wire-format relabel happens in the adapter, not the vendor.** quizazz keeps emitting `quizName`; learningfoundry's `QuizazzProvider` relabels to `assessmentName` before serialization so the `AssessmentManifest` TS interface stays consistent.

This story is docs-only — no executable code changes — and unversioned per the Phase-bundled-release rule (no production-facing impact). The code follow-up lands as a separate story when scheduled.

**Out of scope:**
- Code-side rename of Pydantic models, TS types, SvelteKit components, SQL schema, parameter names — landed as a follow-up story.
- Adding the missing CI/CD Automation section to `tech-spec.md` (template gap noted; separate concern from the rename).
- Renaming the `quizazz` vendor surface — vendor name preserved.

**Tasks:**

- [x] `docs/specs/concept.md`: 5 prose edits ("Quiz and assessment tools" → "Assessment tools", "quiz scores" → "assessment scores" in scope + value mapping, "quizazz for quiz and assessment content" → "quizazz for assessment content"). Problem-space "quiz platforms" landscape mentions preserved.
- [x] `docs/specs/features.md`: 23 edits — YAML discriminator rename in worked example, block-type docs (`**quiz**` → `**assessment**`), all `quiz_scores` / `quiz` references in FR-1 through FR-5 and acceptance criteria, recording-paused-state straggler.
- [x] `docs/specs/tech-spec.md`: 29 edits — `class QuizBlock` → `AssessmentBlock` (+ literal), `class QuizProvider(Protocol)` → `AssessmentProvider`, resolver param `quiz_provider` → `assessment_provider`, SQL schema rename (`quiz_scores`/`quiz_ref`/`quiz_type` → `assessment_*`), TS interfaces `QuizManifest`/`QuizScore` → `AssessmentManifest`/`AssessmentScore` with field renames (`quizName` → `assessmentName`, `quizRef` → `assessmentRef`, `quizType` → `assessmentType`), `QuizManifest` docstring updated to note `QuizazzProvider` relabels the vendor wire key.
- [x] `docs/specs/project-essentials.md`: revisited per refactor_plan Final Step — added (1) "Vendor terminology stops at the vendor boundary" in Domain Conventions, enumerating the preserved vendor surface and the wrong-but-plausible consistency-rename failure mode; (2) "`QuizazzProvider` relabels the manifest wire-format key" in Hidden Coupling, documenting the `quizName` → `assessmentName` adapter responsibility. Updated four stale identifiers (`quiz_scores` table, `QuizProvider`, `QuizManifest`, `quiz` in block-types list).
- [x] Old-file backups (`*_old.md`) created during the per-document cycle; deletion left to developer discretion.
- [ ] No version bump (unversioned per Phase-bundled-release rule).
- [ ] No `CHANGELOG.md` entry (docs-only; not user-visible).

---

### Story J.j: `@types/node` Missing from SvelteKit Template devDependencies [Done]

VSCode reports a TypeScript error on every open of `src/learningfoundry/sveltekit_template/tsconfig.json`:

> Cannot find type definition file for 'node'. The file is in the program because: Entry point of type library 'node' specified in compilerOptions

The auto-generated `.svelte-kit/tsconfig.json` declares `"types": ["node"]` because SvelteKit's internal Vite/build pipeline references node APIs during build. Standard `pnpm create svelte` scaffolds include `@types/node` as a devDependency; this template's [package.json](../../src/learningfoundry/sveltekit_template/package.json) only declares `@types/sql.js`, so the type lookup fails. Production builds via static adapter likely succeed (the runtime output is browser-only), but `svelte-check` / `tsc --noEmit` will report the error and the editor surfaces it persistently.

No production-facing impact (static adapter output doesn't need node types at runtime) — unversioned per the Phase-bundled-release rule.

**Out of scope:**
- Removing the `"types": ["node"]` entry from the generated tsconfig — it's auto-emitted by SvelteKit and not configurable through user config.

**Tasks:**

- [x] `src/learningfoundry/sveltekit_template/package.json`: added `@types/node: ^24.0.0` (Node 24 LTS line) to `devDependencies`.
- [x] `src/learningfoundry/sveltekit_template/pnpm-lock.yaml`: regenerated via `pnpm install --no-frozen-lockfile`; locked `@types/node@24.12.4`.
- [x] Verify: `svelte-check` no longer reports "Cannot find type definition file for 'node'". 24 pre-existing errors (`LessonList.test.ts` Set typing, `vite.config.ts` overload, `database.test.ts` fake-indexeddb declarations, etc.) are unrelated and out of scope. `pyve test` 386 passed; `vitest` 226 passed; `ruff` + `mypy` clean.
- [x] No version bump (unversioned per Phase-bundled-release rule).

---

### Story J.k: `dependency-spec.md` + `pyproject.toml` Extras Name Correction [Done]

Bringing [docs/specs/quizazz/dependency-spec.md](quizazz/dependency-spec.md) and learningfoundry's quizazz extras declaration in line with quizazz's actual shipped surface. Several pre-existing inaccuracies plus updates flowing from the J.i rename.

**Pre-existing bugs (independent of J.i):**

1. **Wrong package name.** dependency-spec says `quizazz-builder` everywhere ("from quizazz_builder import compile_assessment", "pip install learningfoundry[quizazz] installs quizazz-builder", "learningfoundry pins quizazz-builder>=0.1"). quizazz's actual PyPI name is `quizazz` ([quizazz/tech-spec.md:905-906](quizazz/tech-spec.md#L905-L906), [quizazz/README.md:42](quizazz/README.md#L42)). [tech-spec.md:1323-1325](tech-spec.md#L1323-L1325) in learningfoundry's own `pyproject.toml` extras declaration carries the same bug.
2. **Stale Svelte 4 event syntax.** dependency-spec shows `on:complete={handleQuizComplete}`. quizazz now uses Svelte 5 callback-prop convention `oncomplete={handler}` ([quizazz/tech-spec.md:632](quizazz/tech-spec.md#L632)) and dispatches a `CustomEvent('complete')` as legacy-compat — both forms work, but the documented one is stale.
3. **Missing host-side setup steps:** SvelteKit hosts must (a) `import '@pointmatic/quizazz/styles.css'`, (b) disable SSR on routes mounting `<QuizBlock>` (`export const ssr = false;`), and (c) use a Vite-based build so the `?url`-imported WASM asset resolves. None are documented in dependency-spec.
4. **Missing path-escape constraint:** quizazz raises `ValidationError` when `yaml_path` resolves outside `base_dir` ([quizazz/tech-spec.md:842](quizazz/tech-spec.md#L842)) — undocumented in BR-1.

**Rename-driven updates (consequence of J.i):**

5. RR-2 reference to `quiz_scores` table → `assessment_scores`.
6. Data Flow block: `type: quiz` → `type: assessment`; "writes {quizRef, score, maxScore} to its quiz_scores table" → `assessment_scores`.
7. Wire-format mismatch contractualization: quizazz emits manifest key `quizName`; learningfoundry's `AssessmentManifest` TS type uses `assessmentName`. The contract must pin down that learningfoundry's `QuizazzProvider` adapter relabels `quizName` → `assessmentName` before JSON serialization (not the vendor's responsibility). Document this in dependency-spec so the relabeling layer is explicit.
8. `<QuizBlock>` component name **preserved** (vendor surface) — but RR-1 heading "Embeddable Quiz Component" could become "Embeddable Assessment Component" on learningfoundry's side of the contract.

Quizazz itself does NOT need to change — its Python API (`compile_assessment`, `validate_assessment`, `ValidationError`) and SvelteKit component contract (`<QuizBlock>` with `manifest`/`quizRef`/`oncomplete`) already match what learningfoundry needs. The rename is internal to learningfoundry.

No production-facing impact — unversioned per the Phase-bundled-release rule. Doc-only on the learningfoundry side plus a one-line `pyproject.toml` extras-name correction in the tech-spec (the actual `pyproject.toml` fix lands when the code-rename story runs).

**Out of scope:**
- Code changes to quizazz (none required).
- Implementing the `quizName` → `assessmentName` adapter relabel — lands in the code-rename follow-up.

**Tasks:**

- [x] `docs/specs/quizazz/dependency-spec.md`: `quizazz-builder` → `quizazz` (BR-1 constraint, Package Distribution table, Versioning, Testing Contract).
- [x] `docs/specs/quizazz/dependency-spec.md` RR-1: event-handler syntax updated to `oncomplete={handler}`; legacy `CustomEvent('complete')` dispatch documented as also supported.
- [x] `docs/specs/quizazz/dependency-spec.md`: added new RR-4 "Host Setup" covering styles import, per-route `ssr = false`, Vite-based build.
- [x] `docs/specs/quizazz/dependency-spec.md` BR-1: path-escape constraint added — out-of-tree `yaml_path` raises `quizazz.ValidationError`.
- [x] `docs/specs/quizazz/dependency-spec.md`: `quiz_scores` → `assessment_scores` (RR-2 + Data Flow + Testing Contract); `type: quiz` → `type: assessment` (Data Flow).
- [x] `docs/specs/quizazz/dependency-spec.md`: added new RR-1a "Manifest Wire-Format Relabel" pinning the `QuizazzProvider` `quizName` → `assessmentName` translation; Data Flow updated to call out the relabel step; BR-1 behavior cross-references RR-1a; Testing Contract gains a row pinning the relabel as a learningfoundry-owned test.
- [x] `docs/specs/quizazz/dependency-spec.md` RR-1 heading: "Embeddable Quiz Component" → "Embeddable Assessment Component" (component name `<QuizBlock>` preserved on the vendor surface).
- [x] `docs/specs/tech-spec.md` (learningfoundry): `[project.optional-dependencies].quizazz` extras line `quizazz-builder>=0.1` → `quizazz>=0.1` (line 1327).
- [x] No version bump (unversioned per Phase-bundled-release rule).
- [x] No `CHANGELOG.md` entry (docs-only).

**Discovered during implementation, not fixed (out of declared scope):** 7 additional `quizazz_builder` references in `docs/specs/tech-spec.md` outside the extras line — line 52 (dependency table row, same bug class as the extras-line fix); lines 114, 691, 693, 694, 701, 702, 1278 (internal-module path references like `quizazz_builder.validator.validate_file()` describing quizazz's submodule structure). These warrant their own follow-up story since they need to be verified against quizazz's actual submodule layout — the answer isn't a blind `quizazz_builder` → `quizazz` rename if quizazz internally exposes those paths differently.

---

### Story J.l: update remaining `quizazz_builder` references in `tech-spec.md` [Done]

J.k fixed the `[project.optional-dependencies].quizazz` extras line in `tech-spec.md` and the full surface of `quizazz-builder` / `quizazz_builder` references in `dependency-spec.md`. While verifying the J.k work, `grep` surfaced **7 additional `quizazz_builder` references in `tech-spec.md` that J.k did not touch** because the story scoped its `tech-spec.md` edit to a single line. They split into two distinct rename buckets:

**Bucket A — package-name bug (same class as the J.k extras-line fix):**
- [tech-spec.md:52](../../docs/specs/tech-spec.md#L52) — Python dependency table row: `| `quizazz-builder` | `>=0.1` | ...` This is the same "wrong PyPI name" bug J.k fixed at line 1327; the table just lists the dep a second time and was missed.

**Bucket B — stale internal-module path references (over-prescriptive, not a simple rename):**
- [tech-spec.md:114](../../docs/specs/tech-spec.md#L114) — file-tree comment: `# quizazz integration (delegates to quizazz_builder)`
- [tech-spec.md:691](../../docs/specs/tech-spec.md#L691) — `QuizazzProvider` class docstring: "AssessmentProvider implementation backed by quizazz_builder."
- [tech-spec.md:693-694](../../docs/specs/tech-spec.md#L693-L694) — docstring: "Delegates to `quizazz_builder.validator.validate_file()` and `quizazz_builder.compiler.compile_quiz()`..."
- [tech-spec.md:701-702](../../docs/specs/tech-spec.md#L701-L702) — `compile_assessment` docstring step list: "Call `quizazz_builder.validator.validate_file(resolved_path)`. Call `quizazz_builder.compiler.compile_quiz()` with validated output."
- [tech-spec.md:1278](../../docs/specs/tech-spec.md#L1278) — test contract row: "QuizazzProvider delegates correctly to quizazz_builder (mocked)"

**Finding from the live code** (verified via [src/learningfoundry/integrations/quizazz.py:36](../../src/learningfoundry/integrations/quizazz.py#L36)): the actual `QuizazzProvider` does `from quizazz import compile_assessment` and calls that single top-level function — it does **not** import from `quizazz.validator` or `quizazz.compiler` submodules. The Bucket B references in `tech-spec.md` describe an internal multi-step pipeline (`validate_file` then `compile_quiz`) that doesn't match the actual adapter. So Bucket B is not a `quizazz_builder` → `quizazz` rename — it's a **simplification**: collapse the prescribed multi-call delegation to the single `compile_assessment(...)` call the adapter actually makes. Quizazz owns its internal validation-then-compile order; `tech-spec.md` should describe what learningfoundry calls, not what quizazz does internally.

Bucket B also contains adjacent J.i terminology leftovers in the same docstrings (`compile_quiz` is quizazz's older internal name and predates the J.i rename — quizazz now exposes `compile_assessment` at the top level per its current `tech-spec.md`). Folding both layers of staleness into one pass avoids touching the same lines twice.

Doc-only on the learningfoundry side. No production-facing impact. Unversioned per the Phase-bundled-release rule.

**Out of scope:**
- Code-side rename of the `QuizProvider` mention in [integrations/quizazz.py:11](../../src/learningfoundry/integrations/quizazz.py#L11) docstring (`"""QuizProvider implementation backed by the quizazz package."""`) — that's a code-rename concern that belongs with the broader code-side J.i follow-up, not this doc-fix story.
- Any change to quizazz itself (its actual API is correct; the doc is wrong).
- Mass `quizazz_builder` audit across other `docs/` files outside `tech-spec.md` — `grep` after this story lands will catch any further strays as a separate cleanup if they exist.

**Tasks:**

- [x] `docs/specs/tech-spec.md:52` (Bucket A): fixed dependency table row to `| `quizazz` | `>=0.1` | Assessment YAML → JSON manifest compilation (first-party) |`.
- [x] `docs/specs/tech-spec.md:114` (Bucket B): file-tree comment now reads `quizazz integration (delegates to quizazz.compile_assessment)`.
- [x] `docs/specs/tech-spec.md:689-706` (Bucket B): rewrote `QuizazzProvider` class + method docstrings — class docstring now states delegation to the single `quizazz.compile_assessment()` call and notes quizazz owns internal validate-then-compile sequencing; method docstring's step list matches the live adapter shape (lazy-import with install hint, single call, wrap in `IntegrationError`).
- [x] `docs/specs/tech-spec.md:1278` (Bucket B): test-contract row now reads `"QuizazzProvider delegates correctly to quizazz.compile_assessment (mocked); error wrapping"`.
- [x] Verify: `grep` of `docs/specs/` finds no `quizazz_builder` / `quizazz-builder` matches outside (a) `stories.md` narrative describing the J.i / J.k / J.l audit trail, and (b) `.archive/stories-v0.36.0.md` (frozen historical archive). Both are intentional. `pyve test` 386 passed; `ruff` clean; `mypy` clean.
- [x] No version bump (unversioned per Phase-bundled-release rule).
- [x] No `CHANGELOG.md` entry (docs-only).

---

### J.m series overview — `Quiz*` → `Assessment*` code-side rename

J.i was docs-only and explicitly teed up a code follow-up: "Code-side rename of Pydantic models, TS types, SvelteKit components, SQL schema, parameter names — landed as a follow-up story." The J.m series is that follow-up, split into three substories along the natural decoupling lines so each can ship independently in any order.

The vendor-boundary rule from `project-essentials.md` ("Vendor terminology stops at the vendor boundary") draws the firm line that bounds all three substories: everything inside `learningfoundry`'s own surface renames to `Assessment*`; everything that touches the `quizazz` package surface keeps its vendor name. Without that line the rename grows to consume `quizazz` itself, which is wrong (quizazz is a separate package).

**Vendor surface preserved across the whole series (must not rename — guarded by `project-essentials.md`):**
- PyPI package `quizazz` (and the `[project.optional-dependencies].quizazz` extras key)
- npm package `@pointmatic/quizazz`
- SvelteKit component name `<QuizBlock>` (we render it; we don't own it)
- Python adapter class `QuizazzProvider` in `integrations/quizazz.py`
- Test file `tests/test_integrations/test_quizazz.py`
- Component prop `quizRef` on `<QuizBlock>` (vendor prop name)
- Wire-format key `quizName` *as emitted by quizazz* — relabeled to `assessmentName` at the adapter boundary (J.m.2); the downstream `AssessmentManifest` TS type never sees `quizName`.

**Split rationale.** The renames cluster into three independent groups by external contract:
- **J.m.1** — Python-internal protocol + parameter names. Touches no JSON contract, no DB, no TS. Standalone.
- **J.m.2** — JSON wire-format contract: Pydantic `QuizBlock` ↔ YAML `type: assessment` discriminator ↔ TS `AssessmentManifest`/`AssessmentQuestion`/`AssessmentAnswer` types ↔ adapter relabel implementation. **Must ship as one** — Python and TS share the same JSON shape; renaming one without the other breaks `curriculum.json` round-tripping.
- **J.m.3** — Frontend persistence: TS `QuizScore` field rename, SQLite `quiz_scores` table rename with data-loss migration, Svelte component handler renames. Touches no Python, no JSON contract. Standalone.

**Out of scope across the whole series:**
- Renaming the `quizazz` package itself or anything within it (out of repo and out of contract).
- Code-side renames in *quizazz* — quizazz already exposes `compile_assessment` at its top level (post its own rename); learningfoundry consumes that directly.
- A row-copy SQLite migration that preserves learner progress across the schema rename — explicitly chosen against in J.i (data-loss accepted pre-1.0).
- The `<QuizBlock>` component's internal naming (vendor surface; quizazz owns it).
- Renaming the `tests/test_integrations/test_quizazz.py` file — the file tests the adapter, which keeps its `QuizazzProvider` vendor-boundary name.
- README / `features.md` / `tech-spec.md` prose audit beyond what the per-identifier renames force — separate doc-sweep cleanup if needed.

---

### Story J.m.1: v0.70.0 — `QuizProvider` Protocol → `AssessmentProvider` + Parameter Rename [Planned]

Smallest of the three. Renames the Python-internal Protocol type and the `quiz_provider` keyword parameter that flows through `pipeline.py` / `resolver.py`. No JSON contract change (Pydantic class names and YAML discriminators stay untouched here — those are J.m.2). No DB change. No TS change.

**Why this can stand alone:** the `QuizProvider` Protocol is consumed only by learningfoundry's own internal call graph — `pipeline.build()` accepts a `quiz_provider=` keyword and threads it to `resolver._resolve_*` helpers, which dispatch to whatever provider implements `compile_assessment(ref_path, base_dir)`. Renaming the Protocol and the parameter is purely internal Python plumbing; no JSON shape, no on-disk artifact changes.

**Breaking change:** `learningfoundry.pipeline.build()`'s public `quiz_provider=` keyword goes away; callers must use `assessment_provider=`. No alias. Pre-1.0 so acceptable; in practice the public-API consumer count is near-zero today.

**Out of scope (handled in other J.m substories):**
- `QuizBlock` Pydantic class + `type: quiz` discriminator — **J.m.2** (JSON contract).
- TS types and any field-level renames — **J.m.2** / **J.m.3**.
- SQLite schema rename — **J.m.3**.
- Wire-format relabel implementation in `QuizazzProvider.compile_assessment()` — **J.m.2** (the relabel only matters once downstream TS reads the new field name).
- `QuizazzProvider` adapter class docstring tweak from `QuizProvider` → `AssessmentProvider` — done here (lives next to the Protocol rename and is cheaper to land together).

**Tasks:**

- [ ] `src/learningfoundry/integrations/protocols.py`: rename `class QuizProvider(Protocol)` → `class AssessmentProvider(Protocol)`. Method `compile_assessment` already correct.
- [ ] `src/learningfoundry/integrations/quizazz.py`: docstring [line 11](../../src/learningfoundry/integrations/quizazz.py#L11) `"""QuizProvider implementation backed by the quizazz package."""` → `"""AssessmentProvider implementation backed by the quizazz package."""`. Class name `QuizazzProvider` **preserved**.
- [ ] `src/learningfoundry/resolver.py`: rename all `QuizProvider` type annotations → `AssessmentProvider`; all `quiz_provider` parameter names and call-site keywords → `assessment_provider` (lines 15, 101, 110, 124, 147, 178, 190, 198, 215, 263, 292, 304, 323, 335, 428, 432). The `QuizBlock` references at lines 26, 321, 334 are **out of scope here** (J.m.2).
- [ ] `src/learningfoundry/pipeline.py`: rename `QuizProvider` → `AssessmentProvider` (line 14); all `quiz_provider=` parameters and call-sites → `assessment_provider=` (lines 89, 101, 132, 153, 162, 182, 200, 218, 234). Update docstrings ("Override for quiz resolution" → "Override for assessment resolution").
- [ ] `tests/test_phase_j_smoke.py`: `quiz_provider=` → `assessment_provider=` (line 64).
- [ ] `tests/test_smoke_sveltekit.py`: `quiz_provider=` → `assessment_provider=` (line 49). The `quiz_block` locals at lines 229–233 are out of scope (J.m.2).
- [ ] `tests/test_edge_cases.py`: all `quiz_provider=` keyword arguments → `assessment_provider=` (lines 123, 151, 173, 271, 281).
- [ ] Bump version to **v0.70.0** in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [ ] Update `CHANGELOG.md` v0.70.0 entry: `### Changed` (`QuizProvider` Protocol renamed; `quiz_provider=` keyword renamed across `pipeline.build()`, `resolver.*`). `### Removed (BREAKING)`: `QuizProvider` import path, `quiz_provider=` keyword.
- [ ] Verify: `pyve test` passes; `ruff` + `mypy` clean. `grep -rn "QuizProvider\|quiz_provider" src/ tests/` returns no matches.

---

### Story J.m.2: v0.71.0 — JSON Wire-Format Rename (`QuizBlock` + Discriminator + TS Manifest + Adapter Relabel) [Planned]

The tight-couple cluster that has to land together because all four sides describe the same `curriculum.json` shape. Renames the Pydantic block, the YAML discriminator literal, the TS manifest interfaces (`QuizManifest`/`QuizQuestion`/`QuizAnswer`), and lands the long-documented `quizName` → `assessmentName` adapter relabel.

**Why this must ship as one PR:** the four artifacts encode the same contract from different sides — `QuizBlock` (Pydantic, validates input YAML) ↔ `type: assessment` (discriminator literal) ↔ `AssessmentManifest` (TS, types the JSON the frontend reads) ↔ `quizName` → `assessmentName` (adapter relabel that bridges the wire-format key). Renaming any one without the others produces a `curriculum.json` whose schema doesn't match what either end expects, and the runtime failure mode is silent (undefined field) rather than a build-time error.

**Manifest wire-format relabel (RR-1a from `dependency-spec.md`):** the current [integrations/quizazz.py:46](../../src/learningfoundry/integrations/quizazz.py#L46) returns quizazz's dict unchanged, even though `project-essentials.md`, `dependency-spec.md`, and the J.i story all document the contract that `QuizazzProvider.compile_assessment()` relabels `quizName` → `assessmentName` before returning. Latent bug — fix here so the relabel exists by the time the downstream `AssessmentManifest.assessmentName` field starts being read.

**Breaking changes:**
- **Curriculum YAML discriminator:** `type: quiz` → `type: assessment`. Any external curriculum still on the old literal fails to parse loudly. No alias.
- **Python import surface:** `QuizBlock` removed from `schema_v1.py`.
- **TypeScript types:** `QuizManifest`, `QuizQuestion`, `QuizAnswer` removed; field `quizName` removed from the new `AssessmentManifest`.

**Out of scope (handled in other J.m substories):**
- `QuizProvider` Protocol + `quiz_provider` parameter — **J.m.1**.
- `QuizScore` TS type and the SQLite `quiz_scores` table — **J.m.3** (frontend persistence is independent of the JSON wire-format).
- The component-level `onquizcomplete` callback prop name — **J.m.3** (tracks with `QuizScore`, not with the JSON shape).

**Tasks:**

- [ ] `src/learningfoundry/schema_v1.py`: rename `class QuizBlock(StrictModel)` → `class AssessmentBlock(StrictModel)` (line 112). Change discriminator literal from `type: Literal["quiz"]` → `type: Literal["assessment"]`. Update the `ContentBlock` union at [schema_v1.py:132](../../src/learningfoundry/schema_v1.py#L132) to reference `AssessmentBlock`. No backwards-compat alias for the old literal.
- [ ] `src/learningfoundry/resolver.py`: rename remaining `QuizBlock` references → `AssessmentBlock` (lines 26, 321, 334). `isinstance(block, QuizBlock)` → `isinstance(block, AssessmentBlock)`.
- [ ] `src/learningfoundry/integrations/quizazz.py`: implement the wire-format relabel — after calling `compile_assessment(ref_path, base_dir)`, if the returned dict contains a `quizName` key, rename it to `assessmentName` in-place before returning. Document with a one-line comment citing RR-1a / project-essentials. Defensive: if the returned dict already has `assessmentName` (future-proofing), leave it alone.
- [ ] `src/learningfoundry/sveltekit_template/src/lib/types/index.ts`: rename interfaces — `QuizManifest` → `AssessmentManifest` ([line 24](../../src/learningfoundry/sveltekit_template/src/lib/types/index.ts#L24)), `QuizQuestion` → `AssessmentQuestion` (line 32), `QuizAnswer` → `AssessmentAnswer` (line 39). Inside `AssessmentManifest`, rename field `quizName: string` → `assessmentName: string`. Update `ContentBlock` union content type (line 78) and the assessment-specific content block type (line 153) to use `AssessmentManifest`. `QuizScore` reference at lines 220–221 stays as `QuizScore` here — renamed in J.m.3.
- [ ] `src/learningfoundry/sveltekit_template/src/lib/components/ContentBlock.svelte`: type import `QuizManifest` → `AssessmentManifest` (line 10); casts `block.content as QuizManifest` → `as AssessmentManifest` (lines 41, 43). `QuizScore` import at line 7 stays — J.m.3.
- [ ] `src/learningfoundry/sveltekit_template/src/lib/components/module-list.test.ts` (line 135), `LessonList.test.ts` (line 203): fixture content `{ quizName: role, ... }` → `{ assessmentName: role, ... }`.
- [ ] `tests/test_schema_v1.py`: rename `QuizBlock` import → `AssessmentBlock` (line 24); rename `test_quiz_block` → `test_assessment_block` and update body (lines 115–116, 287–307); `quiz_block` locals → `assessment_block` (lines 357–358); discriminator fixtures use `type: assessment`.
- [ ] `tests/test_smoke_sveltekit.py`: `quiz_block` locals → `assessment_block` (lines 230, 233); comment "Quiz pass_threshold" → "Assessment pass_threshold" (line 229).
- [ ] `tests/fixtures/valid-curriculum.yml`: discriminator `type: quiz` → `type: assessment` (line 44); ref filename `assessments/mod-01-lesson-01-quiz.yml` → `assessments/mod-01-lesson-01-assessment.yml` (line 46). Mirror the on-disk fixture file rename.
- [ ] New test in `tests/test_integrations/test_quizazz.py`: pin the wire-format relabel — given a mocked `quizazz.compile_assessment` that returns `{"quizName": "X", ...}`, assert `QuizazzProvider.compile_assessment(...)` returns `{"assessmentName": "X", ...}` with no `quizName` key. Pins the RR-1a contract.
- [ ] Bump version to **v0.71.0** in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [ ] Update `CHANGELOG.md` v0.71.0 entry: `### Changed` (Pydantic `QuizBlock` renamed; YAML discriminator renamed; TS manifest types renamed; wire-format relabel now implemented). `### Removed (BREAKING)`: YAML `type: quiz` literal; `QuizBlock` import; `QuizManifest`/`QuizQuestion`/`QuizAnswer` TS exports; `quizName` field in the emitted manifest.
- [ ] Verify: `pyve test` passes; `pnpm test` passes; `ruff` + `mypy` clean. `grep -rn "QuizBlock\|QuizManifest\|QuizQuestion\|QuizAnswer\|quizName\b" src/ tests/` returns no matches except in `integrations/quizazz.py`'s relabel-implementation comment.
- [ ] Verify: smoke build (`pnpm build`) succeeds — particularly the route that renders `<QuizBlock>`, since the manifest key downstream consumers read has changed.

---

### Story J.m.3: v0.71.1 — Frontend Persistence Rename (`QuizScore` + `quiz_scores` Table + Component Handlers) [Planned]

Frontend-only follow-up. Renames the TS `QuizScore` interface (with `quizRef` field → `assessmentRef`), the SQLite `quiz_scores` table (with data-loss migration per J.i), the `progress.ts` repo methods (`saveQuizScore` / `getQuizScore`), and the Svelte component handlers (`handleQuizComplete` / `onquizcomplete` callback prop). No Python changes; no JSON-contract changes.

**Why this can stand alone:** the `QuizScore` TS interface and the `quiz_scores` SQLite table are *learningfoundry's* internal persistence layer for the score data fired out of `<QuizBlock>`'s `complete` event. The event itself comes from quizazz with vendor field name `quizRef` (preserved per project-essentials), but our consuming handler is free to rename what it does with that data downstream. So this story does the rename at the receiving boundary inward, without touching the vendor surface or the upstream JSON contract.

**Breaking change:** **In-browser SQLite schema** rename with **data-loss migration** per J.i: drop the legacy `quiz_scores` table on next `Database.getDb()`, create `assessment_scores` fresh. No row-copy. Learner progress in the assessment-scores track is lost on upgrade — acceptable pre-1.0; the `lesson_progress` and `exercise_status` tables are unaffected.

**Out of scope (handled in other J.m substories):**
- TS `QuizManifest` and related manifest types — **J.m.2** (JSON contract).
- Pydantic `QuizBlock` and YAML discriminator — **J.m.2**.
- Python `QuizProvider` and `quiz_provider` parameter — **J.m.1**.

**Tasks:**

- [ ] `src/learningfoundry/sveltekit_template/src/lib/types/index.ts`: rename `QuizScore` → `AssessmentScore` (line 208); inside it, rename field `quizRef: string` → `assessmentRef: string`. Update `ModuleProgress.preAssessment` / `postAssessment` references (lines 220–221) to `AssessmentScore`.
- [ ] `src/learningfoundry/sveltekit_template/src/lib/db/progress.ts`: rename method `saveQuizScore` → `saveAssessmentScore` (line 138); `getQuizScore` → `getAssessmentScore`. Update SQL: table `quiz_scores` → `assessment_scores`; column `quiz_ref` → `assessment_ref` (lines 142, 144, 160, 161, 219). Destructuring `[quiz_ref, ...]` → `[assessment_ref, ...]` (line 165). Update comment (line 135) and module docstring (line 5).
- [ ] `src/learningfoundry/sveltekit_template/src/lib/db/database.ts` (or wherever the `CREATE TABLE` lives): update statement to `assessment_scores(...)`. Per J.i decision: **drop the old `quiz_scores` table** during init if present, then create `assessment_scores` fresh. No row copy. Idempotent.
- [ ] `src/learningfoundry/sveltekit_template/src/lib/utils/progress.ts`: comment "Quiz scores and exercise" → "Assessment scores and exercise" (line 8).
- [ ] `src/learningfoundry/sveltekit_template/src/lib/components/LessonView.svelte`: type import `QuizScore` → `AssessmentScore` (line 6); function `handleQuizComplete` → `handleAssessmentComplete` (line 116); callback prop `onquizcomplete={...}` → `onassessmentcomplete={...}` (line 141). The `<QuizBlock>` component prop name on the same line stays — vendor surface.
- [ ] `src/learningfoundry/sveltekit_template/src/lib/components/ContentBlock.svelte`: type import `QuizScore` → `AssessmentScore` (line 7); callback prop type `onquizcomplete?: (score: QuizScore) => void` → `onassessmentcomplete?: (score: AssessmentScore) => void` (line 26).
- [ ] `src/learningfoundry/sveltekit_template/src/lib/components/ProgressDashboard.svelte`: type import `QuizScore` → `AssessmentScore` (line 4); `quizScores` prop and its type → `assessmentScores` (lines 13, 16).
- [ ] `src/learningfoundry/sveltekit_template/src/lib/db/progress.test.ts`: `DELETE FROM quiz_scores` regex → `DELETE FROM assessment_scores` (lines 40, 46); test names `saveQuizScore resolves quietly...` → `saveAssessmentScore resolves quietly...` (line 149) and `getQuizScore returns null...` → `getAssessmentScore returns null...` (line 171); method invocations `repo.getQuizScore(...)` → `repo.getAssessmentScore(...)` (line 173) and `repo.saveQuizScore(...)` → `repo.saveAssessmentScore(...)`.
- [ ] New test in `src/learningfoundry/sveltekit_template/src/lib/db/database.test.ts` (or equivalent): bootstrap a DB with a legacy `quiz_scores` table populated, then trigger init and assert (a) `quiz_scores` is gone, (b) `assessment_scores` exists and is empty, (c) no exception thrown. Pins the data-loss migration contract from J.i.
- [ ] Bump version to **v0.71.1** in `pyproject.toml` and `src/learningfoundry/__init__.py`. (Patch — frontend-internal rename + DB data loss; no Python public-API surface change.)
- [ ] Update `CHANGELOG.md` v0.71.1 entry: `### Changed` (`QuizScore` TS type renamed; `progress.ts` repo methods renamed; Svelte handler callbacks renamed). `### Removed (BREAKING)`: `quiz_scores` SQLite table (data lost on upgrade); `QuizScore` TS export; `saveQuizScore`/`getQuizScore` repo methods; `onquizcomplete` callback prop on `<ContentBlock>`.
- [ ] Verify: `pnpm test` passes; smoke build (`pnpm build`) succeeds. `grep -rn "QuizScore\|quiz_scores\|quiz_ref\|saveQuizScore\|getQuizScore\|onquizcomplete\|handleQuizComplete\|quizScores\b" src/learningfoundry/sveltekit_template/` returns no matches except in the migration test fixture that intentionally creates a legacy `quiz_scores` table. (`quizRef` on its own — without `Quiz` prefix — survives where it's passed to `<QuizBlock>`'s vendor prop.)

---

### Story J.n: `lucide-svelte` 1.0 Migration [Planned]

`lucide-svelte@0.468.0` is marked **deprecated** on npm — the 0.x line is end-of-life and will not receive bug or security fixes. The supported line is 1.x (currently 1.0.1). This is the only deprecated package in the template's dependency graph; every other "newer version available" notice from `pnpm install` is a normal patch/minor diff within the existing caret ranges.

Scope is small: the template imports exactly three icons across two components:
- [Navigation.svelte:4](../../src/learningfoundry/sveltekit_template/src/lib/components/Navigation.svelte#L4) — `ChevronLeft`, `ChevronRight`
- [ResetCourseButton.svelte:7](../../src/learningfoundry/sveltekit_template/src/lib/components/ResetCourseButton.svelte#L7) — `RotateCcw`

Lucide 1.0's primary breaking change is the move from default tree-shaken icon exports to per-icon module imports (`from 'lucide-svelte/icons/chevron-left'`) plus a Svelte 5 runes-native rewrite. Existing barrel imports may still work via a compatibility shim, but the canonical 1.x form is per-icon — worth migrating to match the supported pattern, not just suppressing the deprecation warning.

No production-facing impact on the runtime API of the template (these are icons in navigation and reset controls). Unversioned per the Phase-bundled-release rule.

**Out of scope:**
- Visual redesign of any control that uses these icons.
- Bulk migration of other "newer available" packages (covered by J.o).

**Tasks:**

- [ ] `src/learningfoundry/sveltekit_template/package.json`: bump `lucide-svelte` from `^0.468.0` to `^1.0.1` (or whatever 1.x is current at implementation time).
- [ ] Update the two import sites to the 1.x canonical form (per-icon module imports if the migration guide recommends; otherwise the barrel import if 1.x still supports it cleanly).
- [ ] `src/learningfoundry/sveltekit_template/pnpm-lock.yaml`: regenerate.
- [ ] Verify: `vitest` passes (Navigation and ResetCourseButton component tests exercise the icons); `pnpm dev` renders the icons in browser; `pnpm build` produces no warnings about deprecated imports.
- [ ] No version bump (unversioned per Phase-bundled-release rule).
- [ ] No `CHANGELOG.md` entry (template internals; not user-facing).

---

### Story J.o: Dependabot Wiring for Template + Workspace Dependencies [Planned]

Today the project relies on developer-initiated `pnpm update` / `pip install -U` to pull in security and patch updates. There's no automated signal when a CVE drops against a dependency in `src/learningfoundry/sveltekit_template/package.json` or `pyproject.toml`, and the "newer available" notes from `pnpm install` are the only feedback loop — which mixes security-relevant updates with routine patch noise.

This story wires up GitHub Dependabot via `.github/dependabot.yml` to open weekly PRs for both the Python and SvelteKit-template dependency graphs, with security advisories flowing as a separate, higher-priority signal.

**Why Dependabot (not Renovate or a cadence script):**
- Native to GitHub; no third-party app install required.
- Security advisories file PRs immediately (not on the weekly schedule) — the security signal is what we actually want.
- Configuration is one YAML file in the repo; no out-of-band service to administer.
- Renovate is more configurable but the marginal value over Dependabot is small for a project this size.

**Configuration intent:**
- One ecosystem entry per dependency surface:
  - `pip` against the repo root for `pyproject.toml` / `requirements-dev.txt`.
  - `npm` (Dependabot's name for the JS ecosystem, covers pnpm lockfiles) against `src/learningfoundry/sveltekit_template/` for the SvelteKit template.
  - `github-actions` against `.github/workflows/` so CI action versions don't bit-rot silently.
- Weekly schedule (not daily) to keep PR noise manageable.
- Group patch-and-minor updates per ecosystem into a single weekly PR; major updates land as individual PRs so they can be reviewed deliberately.
- Auto-ignore the `@types/node` major-bump line (we deliberately pin to the LTS major; bumping to odd-numbered "Current" releases is wrong).

**Out of scope:**
- Auto-merge wiring (separate concern; needs branch protection + CI green-gate decisions first).
- Renovate as an alternative (decision baked in above).
- Bulk one-time `pnpm update` to clear the existing backlog of patch/minor diffs — that's a separate cleanup that can land before or after this story.
- `pnpm audit` integration as a CI step (complementary but distinct; the Dependabot security-advisory PR is the primary signal).

**Tasks:**

- [ ] New `.github/dependabot.yml` with three ecosystem entries (`pip`, `npm`, `github-actions`), weekly schedule, grouped patch+minor.
- [ ] Configure the `npm` entry's `directory:` to `/src/learningfoundry/sveltekit_template`.
- [ ] Add an `ignore:` rule for `@types/node` `version-update:semver-major` (LTS-pin rationale).
- [ ] `README.md`: brief mention under a "Maintenance" subsection (or equivalent) noting that Dependabot opens weekly update PRs and security advisories file PRs immediately.
- [ ] Verify: file passes Dependabot's config validator (commit the file; Dependabot lints it on GitHub and surfaces errors in the repository's Insights → Dependency graph → Dependabot tab).
- [ ] No version bump (unversioned per Phase-bundled-release rule).
- [ ] No `CHANGELOG.md` entry (infra; not user-facing).

---

## Future

<!--
This section captures items intentionally deferred from the active phases above:
- Stories not yet planned in detail
- Phases beyond the current scope
- Project-level out-of-scope items
The `archive_stories` mode preserves this section verbatim when archiving stories.md.
-->

- **Cross-tab anti-clobber for the same `userId`.** Two tabs of the same browser, same user, can still last-writer-wins on the IDB blob — Web Locks `+` reload-on-write or BroadcastChannel-based leader election would solve it. Latent issue, distinct from this story; revisit when there's evidence of multi-tab learner workflows or sync work makes it forced. (Same scoping note as I.v.)
- **lmentry integration** — Direct LLM invocation for content generation (currently done externally)
- **nbfoundry real integration** — Replace `NbfoundryStub` with Marimo notebook generation when nbfoundry is published
- **d3foundry real integration** — Replace `D3foundryStub` with D3.js visualization generation when d3foundry is published
- **Reset button** — Course / module / lesson progress reset; defined in sub-plan, deferred from I.j
- **Lesson-level `locked` override** — Per-lesson explicit lock/unlock field in `curriculum.yml`; module-level and sequential rules cover v1 cases
- **Locked lesson tooltip** — Explanation shown when a learner clicks a locked lesson item
- **Curriculum completion screen** — "Course Complete" celebration page reached after the last lesson's Finish
- **Non-YouTube video providers** — Vimeo, self-hosted; VideoBlock currently dispatches `videocomplete` via YouTube IFrame API or viewport fallback only
- **Progress export/import** — Sync or backup learner progress
- **`lessonresume` lifecycle event** — Revisits to lessons already at `complete`. Distinct from `lessonopen` (which fires on every mount including resumes) because it carries the additional invariant "previously completed." Useful for analytics on review behaviour. Deferred from FR-P15 / Story I.p — the data is derivable today from `(getLessonProgress before mount).status === 'complete'`, so the event is sugar rather than new capability.
- **Lifecycle timestamps** — `opened_at`, `engaged_at` columns symmetric with the existing `completed_at`. Deferred from FR-P15 with the explicit reasoning that adding one timestamp at a time yields asymmetric coverage; a coherent treatment covers all transitions, picks a retention/decimation policy, and integrates with whatever telemetry/export story is current at the time.
- **Spaced repetition / adaptive sequencing**
- **Multi-curriculum dashboard**
- **Advanced Testing Infrastructure** - See docs/specs/future-testing-infra-plan.md
- **`pnpm publish` OIDC trusted-publishing gap (upstream).** `pnpm publish` forwards `--provenance` (sigstore signing succeeds and is visible in workflow logs) but skips the GitHub-OIDC-token-for-npm-publish-token exchange — the actual `PUT` to the npm registry then 404s expecting a stored `NPM_TOKEN`. Workaround: drive the publish step with `npm publish` directly while keeping `pnpm` for install/build/validate (this is what quizazz's CI does — see quizazz Story M.f). Worth filing upstream against pnpm; no impact on learningfoundry today since we don't publish to npm. Revisit if learningfoundry ever ships an npm package, or if pnpm closes the gap.
- **Configurable curriculum-style templates.** Phase-J-deferred Feature 4 from [phase-j-pedagogical-authoring-plan.md](phase-j-pedagogical-authoring-plan.md). Different curriculum genres want different pedagogical commitments — a boot-camp curriculum might require every lesson to declare a duration and a role; a self-study curriculum might require nothing. Hard-coding required `meta` fields in `schema_v1.py` is wrong for both. A style template is a curriculum-level config (`curriculum.style: <name-or-path>`) that declares which `meta` fields are required, which `role` values are allowed, and which assessment positions are expected per role. Built-in styles to ship: `minimal` (no meta required, no assessment expectations) and `narrative-survey` (opinionated meta, three-quiz model expected). Validation runs as a layer after Pydantic schema validation. Deferred from Phase J because it depends on Features 1–3 having stabilized; revisit once two or more curricula have authored against the J.a/d/e shapes and the constraint vocabulary is empirically obvious.
- **TypeScript-from-Pydantic type generator.** Eliminate the hidden coupling between [schema_v1.py](../../src/learningfoundry/schema_v1.py) and `lib/types/index.ts` (and between provider return-dict shapes and their TS counterparts) by generating TS types from Pydantic models via `pydantic2ts` (or equivalent) and failing CI when the generated output is stale. Two-part scope: (a) generate from existing Pydantic models in `schema_v1.py`; (b) promote provider return shapes (`ExerciseContent`, `VisualizationContent`, `QuizManifest`) to Pydantic so they're generatable too. Best landed after Phase J ships its expanded meta + assessments schema so the generator covers the full surface from day one. Discriminated unions (content blocks, assessment positions) need explicit Pydantic discriminator config to round-trip cleanly.
- **Sql.js wrapper library extraction.** Both learningfoundry and quizazz consume `sql.js`. The robustness patterns (HEAD-fetch precheck, typed `WasmAssetMissingError`, init memoization, repo-boundary swallow) are documented at [sql-js-wasm-robustness.md](sql-js-wasm-robustness.md). Deliberately *not* extracted into a `@pointmatic/sql-js-kit` package today: N=2 is the classic premature-abstraction trap, the genuinely shared surface is ~60 lines, and the partitioning / UI-surface decisions diverge sharply between the two consumers. Revisit when a third consumer appears, or when learningfoundry and quizazz independently grow mirroring features (schema versioning, multi-DB, sync). Patterns doc travels in the meantime.
