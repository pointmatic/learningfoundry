# Phase J — Assessment Routes Sub-Phase (Plan)

A continuation of Phase J ("Pedagogical Authoring"). Stories J.e and J.f delivered the schema and sidebar-interleave half of module-level assessments; this sub-phase delivers the **functional half** — clickable assessment rows, a dedicated route per assessment, persisted scores, and locking gates.

Source spec: [assessment-route-spec.md](assessment-route-spec.md). That document captures the technical detail; this plan formalizes scope, breaks the work into landable stories, and records the design decisions taken at the approval gate.

The trigger is a consumer-repo end-to-end demo blocked on assessment interactivity — but the spec is the priority, not the demo deadline. Sequencing within the sub-phase is free.

---

## Gap Analysis

### What exists today (post-J.q.1, v0.74.1)

- `AssessmentDefinition` Pydantic model exists with `role`, `position`, `source`, `ref`, `pass_threshold` (Story J.e). `assessments[]` on `Module` is populated and flows into `curriculum.json` verbatim.
- `LessonList.svelte` sidebar interleaves assessment rows in the correct position (Story J.f) — but each row renders as a static `<li>` chip with no `onclick`, no `<a>`, no navigation target. Clicking is a no-op.
- `AssessmentBlock.svelte` → `<QuizBlock>` chain (`@pointmatic/quizazz`) is wired and works — but only invoked when a *lesson content block* has `type: assessment`. Module-level assessments have nowhere to render.
- `progressRepo` (`$lib/stores/progress.ts`) tracks lesson progress (`markLessonOpened` / `markLessonComplete`); the `assessment_scores` table exists (renamed from `quiz_scores` in J.m.4) and stores aggregate score + max_score per lesson-content-block invocation. No per-module-assessment write path exists.
- `locking.ts` plumbs `assessments[]` through `interleaveModuleFlow` for sidebar ordering but does not gate next-module progression on assessment completion or threshold.
- Routes exist only at `[module]/[lesson]/+page.svelte`. No `[module]/assessment/...` route.

### What's needed

1. A stable per-assessment identifier so URLs can be shared, bookmarked, and survive curriculum edits — `AssessmentDefinition` currently has no schema-level `id`.
2. A route file that mounts `<AssessmentBlock>` when a learner clicks a sidebar assessment row.
3. Sidebar assessment rows that are actually clickable, with locked / active visual states matching the lesson rows' idioms.
4. A progress-store write path for per-module-assessment scores (distinct from the existing lesson-content-block path), keyed by `(moduleId, assessmentId)`.
5. Locking logic that treats post-assessment `pass_threshold` as a hard gate on subsequent items, and `role: pre` as a **soft gate** (informational) regardless of threshold.

---

## Feature Requirements

### J-FX1. `AssessmentDefinition.id` field

**Functional**

- Add optional `id: str | None` to `AssessmentDefinition` in `schema_v1.py`.
- When omitted, auto-generate during resolution from `role`: first assessment with a given role keeps the role as id (`pre`, `post`); subsequent ones with the same role append a 1-based counter (`practice`, `practice-2`, `practice-3`). The author can always override by supplying an explicit `id`.
- Validate intra-module uniqueness of effective ids (post-auto-gen) via a `model_validator` on `Module`. Duplicate explicit ids raise a `ValidationError` with module id and the duplicate value.
- `id` passes through `parser` → `pipeline` → `generator.py` into `curriculum.json` verbatim.

**Non-goals for J-FX1**

- No CLI tool to migrate existing curricula. The auto-gen rule means existing YAML continues to work without edits — explicit ids are opt-in.
- No format constraint on `id` beyond uniqueness (matches `Lesson.id` / `Module.id` convention — author responsibility).

### J-FX2. Assessment route

**Functional**

- New route: `sveltekit_template/src/routes/[module]/assessment/[id]/+page.svelte`.
- URL shape: `/{moduleId}/assessment/{assessmentId}`.
- Page derives `moduleId` and `id` from `$page.params`, looks up `module.assessments.find(a => a.id === id)` from the curriculum store, and mounts `<AssessmentBlock>` with `assessmentRef` and `manifest` from the matched entry.
- Completion callback persists score via `progressRepo.markAssessmentComplete(moduleId, assessmentId, score)`.
- Unknown `id` renders "Assessment not found." (parallels existing lesson 404 handling).

### J-FX3. Clickable sidebar assessment rows

**Functional**

- Replace the static `<li>` chip in `LessonList.svelte`'s assessment branch with a `<button>` that navigates to `/{moduleId}/assessment/{assessmentId}`.
- Active state: highlight when `$currentPosition.moduleId === moduleId && $currentPosition.assessmentId === id`. Use the **amber palette** (`bg-amber-100`, `text-amber-800`, `text-amber-600` for the ◆ icon) to visually distinguish assessment-in-progress from lesson-in-progress (blue).
- Locked state: assessments after an unpassed gating post-assessment render `cursor-not-allowed text-gray-300` with `aria-disabled`.

### J-FX4. Progress store — per-module-assessment scores

**Functional**

- Reconcile the existing `AssessmentScore` shape (introduced by J.m.4, persisting lesson-content-block scores) with what the route needs. The route writes `(moduleId, assessmentId, score)`; whatever the existing shape persists today must accommodate the new key without breaking the existing path. Investigation task lives in the story; design decision lives there too.
- Add `markAssessmentComplete(moduleId, assessmentId, score)` and `getAssessmentScore(moduleId, assessmentId)` to `progressRepo`.
- Extend the `$progressStore` value to include an `assessmentScores: Map<string, AssessmentScore>` keyed by `${moduleId}:${assessmentId}` (or equivalent, depending on what J.m.4 chose).
- `passed: boolean` semantics: `score.raw >= assessment.pass_threshold` when threshold is set; `true` when threshold is null (informational assessment).

### J-FX5. Locking integration

**Functional**

- Extend `locking.ts` such that an assessment with `pass_threshold` set acts as a gate: any item appearing **after** it in the `interleaveModuleFlow` output is locked until that assessment has a recorded score with `passed === true`.
- `role: pre` is a **soft gate** regardless of `pass_threshold`: pre-assessments record scores but never lock subsequent items. (Authors who want hard pre-gating use `role: practice` with `position: { before_lesson: ... }` — same effect, more honest naming, no special case.)
- Assessments without `pass_threshold` are informational and never gate.

---

## Technical Changes

### Files touched

**Python (parser / schema):**

```
EDIT   src/learningfoundry/schema_v1.py                          (id field + uniqueness validator)
EDIT   src/learningfoundry/parser.py                             (auto-gen id during resolution, if not done in schema)
EDIT   src/learningfoundry/resolver.py                           (ResolvedAssessment.id pass-through)
EDIT   tests/test_schema_v1.py                                   (id field + uniqueness tests)
```

**SvelteKit template:**

```
EDIT   src/learningfoundry/sveltekit_template/src/lib/types/index.ts   (AssessmentDefinition.id; reconcile AssessmentScore)
NEW    src/learningfoundry/sveltekit_template/src/routes/[module]/assessment/[id]/+page.svelte
NEW    src/learningfoundry/sveltekit_template/src/routes/[module]/assessment/[id]/page.test.ts
EDIT   src/learningfoundry/sveltekit_template/src/lib/components/LessonList.svelte
EDIT   src/learningfoundry/sveltekit_template/src/lib/components/LessonList.test.ts
EDIT   src/learningfoundry/sveltekit_template/src/lib/stores/progress.ts
EDIT   src/learningfoundry/sveltekit_template/src/lib/stores/progress.test.ts
EDIT   src/learningfoundry/sveltekit_template/src/lib/utils/locking.ts
EDIT   src/learningfoundry/sveltekit_template/src/lib/utils/locking.test.ts
```

**Documentation (per-story + closing sweep, see Story Breakdown):**

```
EDIT   docs/specs/features.md          (assessments[] id field; route + gating language; FR-4 per-assessment write path; non-goal #6 softening)
EDIT   docs/specs/tech-spec.md         (AssessmentDefinition.id; curriculum.json example; TS types; assessment_scores schema; package structure tree)
EDIT   README.md                       (Assessments id field; route note in quizazz walkthrough; pass-threshold gating revision; Content locking expansion)
```

### Dependencies

None — no new npm or pip packages.

### Schema migration

`id` is optional with an auto-gen fallback. Existing curricula continue to parse and emit identical `curriculum.json` for assessments where the auto-gen rule produces the historical implicit ordering. Authors who add explicit ids do so opt-in.

---

## Out of Scope

Walked through with developer at planning approval. Decisions:

- **~~Schema-level `id` field on `AssessmentDefinition`.~~** *Pulled in* — see J-FX1. URL stability is much cheaper upfront than retrofit; the implementation is small.
- **Re-attempt UI / score history visualization.** Deferred. Quizazz handles re-attempts internally; we persist the latest score. No usage signal yet to justify a score-history surface.
- **Cross-module assessment dependencies** (e.g., M3 post gates M5 pre). Deferred. Substantial new locking concept (multi-step prerequisite graph) with no current driver. Risk of designing the wrong abstraction speculatively.
- **Skippable pre-assessments with explicit "skip" UI affordance.** Deferred. The soft-gate design (J-FX5) already lets learners proceed past a pre-assessment by clicking the next lesson. An explicit skip button is redundant cosmetic UX — wait for evidence anyone is confused.

---

## Story Breakdown (Preview)

Six stories, appended after `J.q.1` under the existing `## Phase J:` heading. Each story owns the doc surfaces it directly introduces; cross-cutting doc reconciliation is the closing J.w sweep. Each story that ships code takes its own Version Cadence bump.

- **J.r — `AssessmentDefinition.id`: optional field, auto-gen rule, uniqueness validation.** Pydantic + parser + resolver pass-through + tests. Standalone — authors can start using it before the route exists.
  - *Docs in this story:* `tech-spec.md` `AssessmentDefinition` block + `curriculum.json` example; `features.md` FR-2 "Module assessments — generalized array" bullet list; `README.md` "Assessments" subsection.

- **J.s — Assessment route page + page test.** `[module]/assessment/[id]/+page.svelte` plus its sibling test mirroring `[lesson]/page.test.ts`. Depends on J.r.
  - *Docs in this story:* `tech-spec.md` Package Structure tree (add the new route directory); `features.md` FR-3 SvelteKit generation note if a per-assessment route surface needs explicit mention.

- **J.t — Clickable sidebar assessment row.** `LessonList.svelte` button replacement + active/locked palettes + test flip. Depends on J.s for the navigation target.
  - *Docs in this story:* none beyond inline component-level — the cross-cutting "Rows are non-interactive in v1" sentence in `features.md` is owned by the J.w sweep, not this story (because it also depends on J.v's gating landing).

- **J.u — Progress store: per-module-assessment write path.** Investigate the existing `AssessmentScore` shape landed by J.m.4 before designing. Add `markAssessmentComplete` / `getAssessmentScore`, extend `$progressStore`, decide whether the SQLite `assessment_scores` table needs a new column or a new table for module-level assessments (the current PK is `assessment_ref` keyed off content-block-level assessments).
  - *Docs in this story:* `tech-spec.md` TS types (`AssessmentScore` interface) + SQLite `assessment_scores` schema. `features.md` FR-4 if a new write path subsection lands.

- **J.v — Locking: post-assessment threshold gate + soft pre-assessment.** `locking.ts` + tests covering the four cases in the spec (no score / below threshold / above threshold / pre-with-threshold). Soft-gate for `role: pre` is implemented as a design constant, not an authoring opt-in.
  - *Docs in this story:* none in this story — the gating language touches features.md FR-2 + Non-goal #6 + README.md "Content locking" + "Pass-threshold gating" all at once. Owned by J.w.

- **J.w — Phase J Sub-Phase Doc Sweep.** Cross-cutting documentation reconciliation after J.r–J.v ship. Touches:
  - `features.md`: revise the FR-2 "Rows are non-interactive in v1 — gating, per-role styling beyond the label, mid-lesson placement, and assessment-specific routes are deferred." sentence to reflect what actually shipped (routes and post-threshold gating landed; mid-lesson placement and per-role styling still deferred). Soften Non-goal #6 ("Content locking/gating (v1)") to acknowledge post-assessment threshold gating now exists.
  - `README.md`: revise the "Assessments" subsection's `pass_threshold` note (currently "recorded but not gating in v1") and the "Embedding a quizazz assessment" walkthrough to mention module-level navigation; extend "Content locking" to list assessment threshold as a third gating mechanism alongside `sequential` and per-module `locked`.
  - Ship as a doc-only story; no code, no version bump (per Version Cadence — only code-shipping stories bump). Matches the Story J.g precedent (Phase J Close cross-cutting README sweep).

Story dependencies form a partial order — J.r before J.s before J.t; J.u and J.v can be developed in parallel with J.t once J.r/J.s land; J.w runs after J.r–J.v are all done.

---

## Next Mode

After Phase J's last story in this sub-phase ships, the developer prompts to switch to `code_test_first` for implementation of J.r (or the developer may stay in `plan_phase` if further sub-phase planning is needed).
