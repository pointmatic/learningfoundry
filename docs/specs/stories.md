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

### Story J.g: Phase J Close — Cross-Cutting Smoke + README Sweep [Planned]

Final phase-close story that ties off the loose ends each per-feature story didn't pick up:

- A single end-to-end smoke fixture exercising every Phase J affordance simultaneously (lesson + module `meta`, all three tutorial directives, all three assessment roles with mixed positions, `duration_minutes` aggregation). Verifies the features compose cleanly.
- README narrative section "Pedagogical authoring" stitching together the per-feature docs into a single author-facing story with a worked example.
- A migration paragraph in README documenting how to convert `pre_assessment` / `post_assessment` to `assessments[]` for any external curriculum that pre-dates v0.68.0.

No version bump in the title — this story is doc + integration-test only and shares the v0.69.0 release with J.f.

**Out of scope:** new functional behaviour; refactor of any per-story implementation.

**Tasks:**

- [ ] `tests/`: add an end-to-end smoke fixture (curriculum YAML + content) that uses lesson `meta`, module `meta`, all three tutorial directives, all three assessment roles, and `duration_minutes`. Assert the generated `curriculum.json` and rendered SvelteKit DOM contain everything.
- [ ] `README.md`: new "Pedagogical authoring" section with a worked example covering meta blocks, tutorial directives, and the assessments array. Include the migration paragraph for `pre_assessment` / `post_assessment`.
- [ ] `docs/specs/features.md`: a brief "Phase J: Pedagogical Authoring" header tying the per-feature subsections together (insert after J.f's edits).
- [ ] No version bump (shares v0.69.0 with J.f).
- [ ] Verify: `pyve test`, vitest, smoke build, `ruff`, `mypy`.

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
