# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.79.2] - 2026-06-02

Fix sql.js browser-ESM init failure in the SvelteKit template's dev-server preview path. Module and lesson routes were returning 500 in `learningfoundry preview` because `(await import('sql.js')).default` was `undefined` in the browser. Diagnosed in `docs/specs/bug-sql-js-browser-esm-spec.md`; fixed via Story J.y.

### Fixed

- **`vite.config.ts` — `optimizeDeps.exclude` scoped to test mode only.** The exclude was added by Story J.w as a belt-and-braces safety net (J.w's actual fix was the `vi.mock('@pointmatic/quizazz', …)`), but in dev/prod mode it disables Vite's CJS→ESM dep pre-bundling for `sql.js`. Without that pre-bundling layer, the dev-server browser receives `sql.js@1.13+`'s raw UMD `dist/sql-wasm-browser.js`, whose CJS/AMD export branches don't run in pure browser ESM — so `.default` is `undefined` and `initSqlJsFn(...)` throws `TypeError: initSqlJsFn is not a function`. The exclude is now gated on `process.env.VITEST` so vitest 4.x still skips the dep-optimizer (preserving the J.w WASM-magic-header fix) while dev/prod regain CJS-interop.
- **`src/lib/db/database.ts` — typed `CjsEsmInteropError` backstop.** The dynamic `import('sql.js')` site now reads `.default` defensively and throws a named `CjsEsmInteropError` instead of an opaque `TypeError` when the initializer is missing. So the *next* sql.js drift surfaces a self-describing error in the dev-server console rather than the previous unactionable shape.

### Verified

- `pnpm exec vitest run` → 278 passed (was 277; +1 new contract test for the CJS/ESM interop guard).
- `pnpm exec svelte-check` → 0 errors, 0 warnings.
- `pnpm exec vite build` → succeeds (confirms the gated `optimizeDeps.exclude` doesn't break prod build; the J.w comment's "covers both prod build" framing was incorrect).
- Manual: dev-server `/{moduleId}/{lessonId}` route renders without 500 in the d802-deep-learning consumer (verification scheduled with the consumer team — captured as a `[ ]` follow-up).

## [0.79.1] - 2026-05-22

Fix five pre-existing `svelte-check` and `vitest` failures uncovered after the J.v post-assessment work landed (Story J.w). All five are type-only or test-only — no runtime behaviour changes.

### Fixed

- **`vite.config.ts` typed `test` block.** `defineConfig` is now imported from `vitest/config` so the `test` field type-checks under `svelte-check`. The redundant `/// <reference types="vitest" />` triple-slash directive is removed in the same edit. A top-level `optimizeDeps: { exclude: ['sql.js'] }` is added as a safety belt for future scenarios where learningfoundry-owned code statically imports `sql.js`.
- **`LessonView.test.ts` lesson cast.** Replaced the brittle `Parameters<typeof render>[1] extends { props: infer P } ? P : never` conditional cast (which now resolves to `never` under `@testing-library/svelte`'s updated `render` signature) with the file-local convention `as unknown as never` already used by the J.b tagline tests.
- **`database.test.ts` `fake-indexeddb` subpath import.** `fake-indexeddb@6.x` ships type declarations only at the package root and `/auto`, not at `/lib/FDBFactory`. Switched to the typed named export: `import { IDBFactory as FDBFactory } from 'fake-indexeddb';`.
- **`VideoBlock.test.ts` `MockPlayer` constructability.** Vitest 4.x stopped wrapping `vi.fn().mockImplementation((…) => { … })` so arrow-function impls are no longer constructable via `new`. Changed both `MockPlayer` definitions to regular `function (…) { … }` impls. The dependent `IntersectionObserver is not defined` error in the rerender test was a cascade from the same root cause and is resolved by the same fix.
- **`LessonView.test.ts` / `routes/[module]/[lesson]/page.test.ts` quizazz mock.** Added `vi.mock('@pointmatic/quizazz', …)` to both files. `@pointmatic/quizazz`'s bundled `dist/db/database.js` contains a static `import wasmUrl from 'sql.js/dist/sql-wasm.wasm?url';` — vite-only syntax. Under vitest/Node ESM the `?url` query is stripped, Node treats the `.wasm` path as an ESM WebAssembly module, and fails to resolve Emscripten's synthetic `"a"` env import. The failing tests never actually render `<QuizBlock>` (their lessons are text-only or empty), so a module-surface stub is sufficient and intercepts the chain at the quizazz boundary.

### Verified

- `pnpm exec svelte-check` → 0 errors, 0 warnings (was 3 errors).
- `pnpm exec vitest run` → 277 passed (was 265 passed / 12 failed).
- `pyve test` → 411 passed.
- `ruff` clean, `mypy` clean.

## [0.79.0] - 2026-05-22

Post-assessment threshold gating + soft pre-assessment convention (Story J.v). With J.u's per-module-assessment scores now persisting, locking finally consumes them: a threshold-bearing non-pre assessment gates every item that appears after it in `interleaveModuleFlow`, and the next module stays sequentially locked until the assessment passes. `role: pre` is the deliberate exception — diagnostic pre-assessments are soft-gates per the J.v sharp-edge resolution, so even an unpassed pre-assessment with a `pass_threshold` set does not lock lesson 1. The `lockedAssessments: Set<string>` prop on `<LessonList>` (added in J.t with an empty default) is finally fed real data.

### Added

- **`lockedItemsInModule(moduleId, curriculum, progress)`** in [lib/utils/locking.ts](src/learningfoundry/sveltekit_template/src/lib/utils/locking.ts) — walks `interleaveModuleFlow` in canonical order and returns `{ lockedLessons, lockedAssessments }`. Combines two orthogonal rules: the existing `lesson_sequential` lock-on-prior-incomplete, plus the new assessment-threshold gate (once any threshold-bearing non-pre assessment is unpassed, every subsequent flow item locks — including later assessments).
- **`lockedAssessmentIds(moduleId, curriculum, progress)`** — assessments-only projection of `lockedItemsInModule`. Consumed by `<ModuleList>` and passed into `<LessonList>`'s `lockedAssessments` prop.
- **11 new locking tests** in [lib/utils/locking.test.ts](src/learningfoundry/sveltekit_template/src/lib/utils/locking.test.ts) covering the six J.v acceptance cases plus extra coverage:
  - Post-assessment unrecorded → next module locked.
  - Post-assessment below threshold → next module locked.
  - Post-assessment at/above threshold → next module unlocked.
  - Pre-assessment unrecorded (with threshold) → lesson 1 still unlocked (soft-gate).
  - Two post-assessments in sequence: passing the first but not the second locks the third module.
  - Threshold-null assessment is informational; never gates.
  - `{before_lesson: <id>}` threshold-gate locks that lesson + everything after.
  - A later assessment downstream of an unpassed earlier gate renders locked itself.
  - `lockedAssessmentIds` projection matches expected set shape.
  - Pre-assessment with threshold doesn't block `isModuleComplete`.
  - Informational assessment inside a module doesn't lock subsequent items.

### Changed

- **`isModuleComplete`** in `locking.ts` extends to also require every threshold-bearing non-pre assessment to be passed (per `computeAssessmentPassed`). This is the propagation channel that makes the cross-module rule work: the sequential-locking check already consults `isModuleComplete(prev)`, and now an unpassed post-gate keeps that returning false. `role: pre` exempt (soft-gate).
- **`lockedLessonIds`** refactored to a wrapper that returns `lockedItemsInModule(...).lockedLessons`. Lesson-sequential locking still works identically; the new layer adds assessment-gate locking on top.
- **[components/ModuleList.svelte](src/learningfoundry/sveltekit_template/src/lib/components/ModuleList.svelte)** — computes `lockedAssessments` via `lockedAssessmentIds(...)` and passes it into `<LessonList>` alongside the existing `lockedLessons`. This is what makes the J.t locked-state styling visible in production.

### Notes

- **`role: pre` soft-gate is the only special case in the locking logic.** Authors who want hard pre-gating use `role: practice` with `position: { before_lesson: <id> }` — same gating effect via the generic rule, no separate code path needed (matches the project-essentials guidance under "Pre-assessments are a non-locking soft-gate by convention").
- **No backwards-compat shim.** Pre-J.v modules with threshold-bearing assessments-without-scores had previously been treated as "complete" (the threshold was recorded but not gating in v1). Post-J.v those modules are `not_complete` until the assessment passes. Acceptable pre-1.0; downstream curricula that relied on the old behaviour can either drop the `pass_threshold` (making the assessment informational) or accept the gate.
- **Cross-module assessment dependencies, score-history-aware gating, and pre-assessment "skip" UI affordances remain out of scope** (matches the story spec's OOS list).
- **The pre-existing 12 vitest failures (LessonView, lesson route, VideoBlock) + 3 svelte-check errors** are still unaddressed. Story J.w now exists to track them as a `debug` cycle.

## [0.78.0] - 2026-05-22

Per-module-assessment progress write path (Story J.u). With Story J.s's route + J.t's clickable sidebar in place, completing a module-level assessment now actually *persists*. The chosen reconciliation path (Option B per the J.u investigation gate) is a new sibling `module_assessment_scores` table keyed on `(module_id, assessment_id)` — the content-block `assessment_scores` table (keyed on global `assessment_ref`) stays as-is. The two write paths are genuinely different domains: a content-block ref is curriculum-globally unique, while two modules can legitimately reuse the same quizazz YAML so its identity at module level has to include the module id.

### Added

- **New SQLite table `module_assessment_scores`** in [database.ts](src/learningfoundry/sveltekit_template/src/lib/db/database.ts) with PK `(module_id, assessment_id)` and the standard score/maxScore/questionCount/completed_at columns. The table is created idempotently via `CREATE TABLE IF NOT EXISTS` alongside `assessment_scores` (which is unchanged).
- **`ModuleAssessmentScore` TS interface** in [types/index.ts](src/learningfoundry/sveltekit_template/src/lib/types/index.ts) carrying `moduleId`, `assessmentId`, `score`, `maxScore`, `questionCount`, `completedAt`. `AssessmentScore` is unchanged.
- **`progressRepo.markAssessmentComplete(moduleId, assessmentId, score)`** in [db/progress.ts](src/learningfoundry/sveltekit_template/src/lib/db/progress.ts) — accepts the `AssessmentScore` shape that `<AssessmentBlock>` already builds (so the route doesn't have to translate at the call site) and drops the `assessmentRef` field at the persistence boundary; the module-level table doesn't carry it.
- **`progressRepo.getAssessmentScore(moduleId, assessmentId)`** — new overload of `getAssessmentScore` returning `ModuleAssessmentScore | null`. The pre-existing single-arg variant (lookup by global `assessmentRef`) was renamed to `getAssessmentScoreByRef` to free the canonical name.
- **`computeAssessmentPassed(score, passThreshold)`** helper in [lib/utils/assessment-passed.ts](src/learningfoundry/sveltekit_template/src/lib/utils/assessment-passed.ts) — pure read-time `passed: boolean` derivation. Returns `true` when `passThreshold` is null/undefined (informational assessment), `false` when `maxScore` is 0 with a non-null threshold, else `score / maxScore >= threshold`. Read-time evaluation lets a future YAML threshold tweak re-evaluate against the active rule instead of staying frozen to whatever was true at write time.
- **`ModuleProgress.assessmentScores: Record<string, ModuleAssessmentScore>`** — the new field is keyed by `assessmentId`. `getModuleProgress` now loads from `module_assessment_scores` in addition to `lesson_progress`.
- **Route wiring** in [routes/\[module\]/assessment/\[id\]/+page.svelte](src/learningfoundry/sveltekit_template/src/routes/[module]/assessment/[id]/+page.svelte) — the J.s no-op `handleComplete` stub is replaced with the real `progressRepo.markAssessmentComplete(moduleId, assessmentId, score)` invocation, followed by `invalidateProgress(...)` so the sidebar / dashboard pick up the new score without a page reload.
- **Tests** — 9 new cases in [progress.test.ts](src/learningfoundry/sveltekit_template/src/lib/db/progress.test.ts) covering the SQL write contract (PK clause, no `assessment_ref` column), persistence side effect, collision isolation across modules sharing an `assessmentRef`, the read SQL shape, full row deserialization, null-on-no-row, and `getModuleProgress` loading the assessment-scores map. 8 new cases in [assessment-passed.test.ts](src/learningfoundry/sveltekit_template/src/lib/utils/assessment-passed.test.ts) covering all the `computeAssessmentPassed` branches. 1 new case in the route's [page.test.ts](src/learningfoundry/sveltekit_template/src/routes/[module]/assessment/[id]/page.test.ts) asserting `markAssessmentComplete` is invoked with the URL-derived `(moduleId, assessmentId)` plus the score, and that `invalidateProgress` runs afterward.

### Changed

- **`ModuleProgress` reshape — drop `preAssessment` / `postAssessment`, add `assessmentScores`.** The pre-J.e two-slot fields had been carrying `null` since J.e generalized to the assessments-array shape; J.u retires them in favour of the keyed map. ~5 test files (`stores/progress.test.ts`, `utils/progress.test.ts`, `utils/locking.test.ts`, `components/ModuleList.test.ts`, `components/ProgressDashboard.test.ts`) updated to drop the legacy boilerplate.
- **`progressRepo.getAssessmentScore(assessmentRef)` renamed to `getAssessmentScoreByRef(assessmentRef)`** to free the canonical name for the new `(moduleId, assessmentId)` overload. There were no production consumers of the renamed method; only tests referenced it.
- **`resetProgress` SQL** — adds `DELETE FROM module_assessment_scores` to the transaction so the course-level reset truncates the new table too.
- **[tech-spec.md](docs/specs/tech-spec.md) SQLite DDL block + TypeScript types** updated to match current schema: `assessment_scores` row shape corrected to current production reality (the spec text was carrying obsolete `module_id` / `assessment_type` columns that haven't been in the actual schema since J.m.4), and the new `module_assessment_scores` table + `ModuleAssessmentScore` interface added. `ModuleProgress` interface in the spec replaces `preAssessmentScore` / `postAssessmentScore` slots with `assessmentScores: Record<string, ModuleAssessmentScore>`.
- **[features.md](docs/specs/features.md) FR-4** — sub-bullet 3 expanded to name both write paths (`saveAssessmentScore` vs. `markAssessmentComplete`) and the underlying tables; sub-bullets 1 and 6 (schema-init list, reset-truncate list) name `module_assessment_scores` alongside the existing tables.

### Notes

- **Forward-only data-loss migration.** Pre-J.u progress in `assessment_scores` survives (that table is unchanged). The new `module_assessment_scores` table starts empty for every installed learner. There is no backfill from `assessment_scores` to `module_assessment_scores` — a curriculum that had both a content-block assessment and a module-level assessment pointing at the same YAML would record separately; this is the correct semantics (different placement contexts) but worth documenting.
- **Locking enforcement is still deferred to J.v.** This story persists the score and exposes it through `progressStore` and `getAssessmentScore(moduleId, assessmentId)`; J.v adds the `pass_threshold` gate that consumes `computeAssessmentPassed` to lock subsequent items in the module flow.
- **Re-attempts overwrite.** `markAssessmentComplete`'s `ON CONFLICT … DO UPDATE` keeps only the latest score. Multi-attempt history is a deferred OOS item from the source spec; quizazz already retains per-question history in its own IndexedDB databases per the J.i terminology contract.

## [0.77.0] - 2026-05-22

Clickable sidebar assessment row (Story J.t). With Story J.s's route in place, the sidebar's module-assessment row finally becomes the navigation control it always implied it was: a `<button>` that drives `goto('/{moduleId}/assessment/{id}')`, lights up amber when its assessment is the one currently being attempted, and renders a grey `aria-disabled` state when locked. The locking signal (`lockedAssessments`) is a prop-shaped seam wired into the component but fed an empty set until Story J.v ships the actual gate logic.

### Added

- **`currentPosition.assessmentId`** in [stores/curriculum.ts](src/learningfoundry/sveltekit_template/src/lib/stores/curriculum.ts) — `NavPosition` gains an optional `assessmentId: string | null` field; `lessonId` widens to `string | null`. Mutual-exclusion is enforced by the setters: `navigateTo(...)` writes `{ moduleId, lessonId, assessmentId: null }`, the new `setAssessmentPosition(moduleId, assessmentId)` writes `{ moduleId, lessonId: null, assessmentId }`. Lesson-side derived stores (`currentLesson`, `currentIndex`) treat null `lessonId` as "not on a lesson" and return null / -1.
- **Clickable assessment row** in [components/LessonList.svelte](src/learningfoundry/sveltekit_template/src/lib/components/LessonList.svelte) — the static `<li>` chip is now an inner `<button>`. `onclick` calls `goto('/${moduleId}/assessment/${assessment.id}')` unless the row is locked. Active state lights up the **amber palette** (`bg-amber-100 font-medium text-amber-800`, ◆ in `text-amber-600`) when `$currentPosition.moduleId === moduleId && $currentPosition.assessmentId === assessment.id` — intentionally distinct from the blue lesson-active palette so learners can tell at a glance whether they're in an assessment or a lesson. Locked state: `cursor-not-allowed text-gray-300`, `aria-disabled="true"`, ◆ also greyed; click is a no-op.
- **`lockedAssessments?: Set<string>` prop** on `LessonList.svelte` — defaults to empty. Story J.v's locking pass will populate this from `locking.ts`; until then the seam exists so consumers can wire it without LessonList shape changes later.
- **Route → store sync** in [routes/\[module\]/assessment/\[id\]/+page.svelte](src/learningfoundry/sveltekit_template/src/routes/[module]/assessment/[id]/+page.svelte) — `onMount` + `$effect` call `setAssessmentPosition(moduleId, assessmentId)` when the matched assessment exists. Mirrors the lesson route's URL→store pattern; without it the sidebar amber-active state would never light up in production.
- **6 new LessonList tests** under `describe('LessonList mount — clickable assessment rows (Story J.t)')` — button shape, click navigation target, amber active state via a real `currentPosition` writable mock, default gray palette when inactive, locked-state attributes/styles/click suppression, and the `lockedAssessments` default-empty behaviour.
- **3 new curriculum-store tests** under `describe('setAssessmentPosition (Story J.t)')` — sets `{ moduleId, lessonId: null, assessmentId }` without calling `goto`, and the two mutual-exclusion transitions (lesson → assessment, assessment → lesson) clear the opposing field.

### Changed

- **[components/navigation.helpers.ts](src/learningfoundry/sveltekit_template/src/lib/components/navigation.helpers.ts)** — `resolveGoNext` / `resolveGoPrev` add a `lessonId` non-null guard. Lesson-sequence positions are always lesson-only at runtime, so this is a TS-shape concession to the new `NavPosition.lessonId: string | null`; behaviour unchanged.
- **Existing `LessonList.test.ts` interleaved-rows test** — moves its `data-role` lookup from `li.getAttribute('data-role')` to `li.querySelector('[data-role]')`, since `data-role` now sits on the inner `<button>`. Existing `[data-testid="assessment-row"]` selectors keep working (the attribute moved with the role to the button).
- **Existing `curriculum.test.ts` navigateTo / navigateNext / navigatePrev assertions** — `toEqual` shapes updated to include `assessmentId: null` (the new explicit-clears-the-other-field contract).
- **Test-file Set typing** — 13 `new Set()` instances across `LessonList.test.ts` parameterized to `new Set<string>()`. Incidental cleanup; resolved 13 pre-existing svelte-check `Set<unknown>` errors that would otherwise have grown alongside the new tests.

### Notes

- The lock determination itself is **deliberately not in this story** — `lockedAssessments` is whatever the caller passes in, default empty. Until J.v, no assessment renders locked in production. The visual state is exercised only by tests.
- The new route is now reachable both by URL and by sidebar click, but learners still can't be locked out of it — the locking story (J.v) closes that loop.
- Mid-lesson placement, keyboard-nav refinements beyond native `<button>` focus, and per-role styling beyond amber-active / grey-locked remain deferred (matches the story's "Out of scope" list).
- Pre-existing svelte-check errors went from 23 → 3 as a side effect of fixing the Set typing in tests I touched. The remaining 3 (vite.config `test` field, LessonView.test cast, fake-indexeddb declaration) predate this work.

## [0.76.0] - 2026-05-22

Module-level assessment route layer (Story J.s). Until this story, the sidebar's module-assessment rows had nowhere to navigate — `<AssessmentBlock>` was only invoked from inside `LessonView`'s content-block chain. v0.76.0 adds the `[module]/assessment/[id]/` route so module-level assessments are reachable by URL. Sidebar interactivity (J.t), per-module persistence wiring (J.u), and locking enforcement (J.v) land in subsequent stories.

### Added

- **`routes/[module]/assessment/[id]/+page.svelte`** — new SvelteKit route. Derives `moduleId` / `id` from `$page.params`, looks up `module.assessments.find(a => a.id === id)` in the curriculum store, and mounts `<AssessmentBlock>` with `assessmentRef={assessment.ref}`, `manifest={assessment.content}`, `passThreshold={assessment.pass_threshold ?? 0.0}`. Header shows `{capitalizeRole(role)} Assessment`. Completion is wired to a no-op `handleComplete(score: AssessmentScore)` stub — J.u replaces it with `progressRepo.markAssessmentComplete(moduleId, id, score)`. Unknown id (or unknown module) renders "Assessment not found." (parallels the lesson 404 branch).
- **`routes/[module]/assessment/[id]/page.test.ts`** — 5 vitest cases mirroring `AssessmentBlock.test.ts`'s stub strategy. Asserts: `<AssessmentBlock>` receives correct `assessmentRef` + `manifest`; the capitalized role label renders in the header; "Assessment not found." renders on unknown assessment id and on unknown module id; the route's completion callback signature accepts `AssessmentScore` (J.u-ready contract).

### Changed

- **[tech-spec.md](docs/specs/tech-spec.md)** Package Structure tree — adds the new `assessment/[id]/+page.svelte` route under `[module]/` alongside `[lesson]/`.

### Notes

- The progress-store write path (`markAssessmentComplete`) is deliberately out of scope. `<AssessmentBlock>` still persists per-assessment scores via `progressRepo.saveAssessmentScore` (its standard behaviour, untouched here); only the higher-level "module-assessment completed" hook is stubbed. J.u introduces the new `(moduleId, assessmentId)` key shape so two modules' assessments can share a `ref` without collision.
- The new route is reachable only by typing the URL directly. The sidebar's assessment row stays a static `<li>` until Story J.t.
- Pre-existing vitest failures in `LessonView.test.ts`, `VideoBlock.test.ts`, and `routes/[module]/[lesson]/page.test.ts` (12 cases) predate this story and are unrelated. Documented for visibility; their fix belongs in a separate `debug` cycle.

## [0.75.0] - 2026-05-22

Stable per-assessment identifier for module-level assessments (Story J.r). Foundation for the upcoming assessment route layer (J.s) and the progress-store write path (J.u): both need to address a single assessment within a module by something that survives author-order edits. Without an id, the route layer would have to fall back to array indices, and URLs would shift every time an author inserts or reorders an entry.

### Added

- **`AssessmentDefinition.id` field** in [schema_v1.py](src/learningfoundry/schema_v1.py) — optional `str | None`, defaults to `None`. When omitted, a new `Module.autogen_assessment_ids` `model_validator(mode="after")` fills it in from `role`: the first assessment with a given role gets the bare role as id (`pre`, `post`, `practice`), the Nth (N>1) appends a 1-based counter (`practice-2`, `practice-3`). Explicit ids are honoured verbatim. A second pass over the populated id set raises `ValidationError` on any duplicate, naming the module id and offending id — so explicit duplicates **and** explicit ids colliding with auto-gen results both fail loud at parse time.
- **`ResolvedAssessment.id`** in [resolver.py](src/learningfoundry/resolver.py) — non-optional `str`, threaded verbatim from the parsed `AssessmentDefinition` (auto-gen guarantees a value by the time the resolver runs). Serialized into `curriculum.json` via the existing `dataclasses.asdict` path; no generator changes required.
- **`AssessmentDefinition.id` in TS types** in [lib/types/index.ts](src/learningfoundry/sveltekit_template/src/lib/types/index.ts) — non-optional `string` in the resolved JSON, matching the auto-gen guarantee.
- **README "Assessments" subsection** ([README.md](README.md)) — documents the `id` field, the auto-gen rule, and a worked example mixing auto-gen and explicit ids.
- **4 new test cases** in [tests/test_schema_v1.py](tests/test_schema_v1.py) under `TestAssessmentIdAutoGen` — covering all-omitted auto-gen, mixed explicit + omitted, duplicate explicit rejection, and explicit-colliding-with-auto-gen rejection.

### Changed

- **[tech-spec.md](docs/specs/tech-spec.md)** — `AssessmentDefinition` model block shows the new `id` field; new `Module.autogen_assessment_ids` validator listed; `ResolvedAssessment` dataclass and curriculum.json example both include the `id` field; SvelteKit TS `AssessmentDefinition` interface updated.
- **[features.md](docs/specs/features.md)** — FR-2 "Module assessments — generalized array" subsection has a new `id` bullet covering the auto-gen rule and uniqueness enforcement.

### Notes

- No CLI migration tool — existing curricula continue to parse unchanged because auto-gen fills in every omitted id. Authors opt into explicit ids when they want stable URLs (e.g. `diagnostic` instead of `pre`) or to lock the id against future reorderings.
- Format constraints on `id` are intentionally limited to uniqueness — no kebab-case enforcement, matching the `Lesson.id` / `Module.id` convention where format is author responsibility (those enforce kebab-case at the schema level via `_validate_id`, but assessment ids are addressed in URLs and may want author-chosen forms; revisit if a real failure mode surfaces).

## [0.74.1] - 2026-05-22

PyYAML flow-context gotcha surfaced by downstream authoring against the J.h/J.q schema-extensions grammar. The J.h worked example used a YAML form that fails to parse — copy-paste authors hit `expected ',' or '}', but got '['` from PyYAML with no indication of the fix. Story J.q.1: docs fix + targeted validator hint, scoped to the one quirk that reproduces against the declared dependency floor.

### Added

- **Validator hint for `list[T]`-in-flow-mapping PyYAML quirk** — `load_schema_extensions` ([schema_extensions.py](src/learningfoundry/schema_extensions.py)) now recognises the failure signature (`expected ',' or '}'` + `got '['` in the PyYAML error) and appends a hint to the wrapped `SchemaExtensionError` naming the two safe forms (quoted-flow `{ type: "list[str]" }` or block style). The hint matcher is brittle-by-design (fails open → no hint, never worse error) — a companion robustness test in `tests/test_schema_extensions.py::TestPyYamlFlowContextHint::test_pyyaml_wording_unchanged` reproduces the raw PyYAML failure and asserts the matcher's keyed substrings are still present, so a future PyYAML wording drift surfaces as a test failure first.
- **Project-essentials Architecture Quirks entry** — new "Schema-extensions YAML — PyYAML `list[T]` in flow mapping quirk" subsection in [project-essentials.md](docs/specs/project-essentials.md) documenting the signature, both safe forms, and the matcher's brittleness-by-design posture so future LLMs editing extension files default to a safe form and don't go hunting for a phantom learningfoundry bug.

### Changed

- **README J.h worked example fixed** — [README.md:528, 530](README.md) — the two `{ type: list[str], default: [] }` lines now use the quoted-flow form (`{ type: "list[str]", default: [] }`). A "YAML gotcha" callout below the example names the PyYAML signature and the two safe forms.
- **PyYAML floor pinned to `>=6.0.3`** — [pyproject.toml:28](pyproject.toml#L28). The previous `>=6.0` was open-ended; pinning to a version definitively-known-to-handle the matcher contract removes one variable from the dependency surface.

### Notes

- The reported "nested flow sequence inside flow mapping" quirk (`{ type: enum, values: [a, b, c] }`) does **not** reproduce against PyYAML 6.0.3. Six minimal variants and a full schema-extensions-context reproduction all parsed cleanly. Documenting a quirk that does not reproduce in the declared dependency floor would confuse future readers; J.q.1 scopes to the verified `list[T]` quirk only and parks the nested-flow-sequence report for a future story if a concrete reproducer surfaces (older PyYAML, more exotic construct).
- 4 new test cases in [tests/test_schema_extensions.py](tests/test_schema_extensions.py) covering both happy paths (`list[str]` and `list[object]`), the unrelated-YAML-error guard (signature-specific matcher, not blanket-on), and the PyYAML wording robustness assertion.

## [0.74.0] - 2026-05-21

Schema-extensions grammar extension (Story J.q) — adds two new discriminated-union variants on top of the J.h foundation so authors can declare structured nested data instead of smuggling it through `extra="allow"` or flattening it into string conventions.

### Added

- **`object` field type** in [`learningfoundry-schema-extensions.yml`](src/learningfoundry/schema_extensions.py) — declares a single nested object via an inner `fields:` block that reuses the full grammar (including further-nested `object` / `list[object]`). `extra: forbid` by default at every nesting level, per-object `extra: allow` opt-out for staged tightening. No `default:` field is declared on `ObjectFieldDef`; writing `default:` next to `type: object` is rejected at load time by the strict `extra="forbid"` of the extension-file model — use `required: false` to make the whole object optional instead.
- **`list[object]` field type** in the same file — declares a list of nested objects with the element type built from the inner `fields:` block. Only `default: []` is meaningful; a `model_validator(mode="after")` rejects any non-empty list default at load time. Synthesized element-model names follow the deterministic scheme `<parent>__<field>__Item` (e.g. `CurriculumMeta__citations__Item`) so Pydantic `loc` paths in error messages stay readable.
- **Forward-reference resolution** — `ObjectFieldDef.fields` and `ListObjectFieldDef.fields` are forward references into the same `FieldDef` discriminated union that lists them. Explicit `ObjectFieldDef.model_rebuild()` / `ListObjectFieldDef.model_rebuild()` calls at module import time force resolution then rather than failing in user code with a confusing Pydantic forward-ref error.
- **Recursive nested-model builder** — new `_build_object_model(name, fields_def, extra_mode)` walks the declared inner `fields:` map and recursively synthesizes Pydantic models for every nested `object` / `list[object]` via `_object_field_entry`. The same name scheme applies at arbitrary depth.
- **README** "Strict project-specific extensions" subsection extended with a worked `object` / `list[object]` example (`citations` + `provenance` from a real CNN-curriculum authoring case) and a sentence on the `default:` rejection rules.
- 17 new test cases in [`tests/test_schema_extensions.py`](tests/test_schema_extensions.py) covering valid round-trips, unknown-key rejection at depth, `required: false` omission, `default:` rejection on both variants, `extra: allow` opt-out, deeply nested (depth-3) declarations, forward-ref resolution, and the deterministic-name invariant.

### Notes

- No change to the runtime API of generated curricula. The base `CurriculumMeta` / `ModuleMeta` / `LessonMeta` models are unchanged; the new variants are only reachable through a project-supplied `learningfoundry-schema-extensions.yml`.
- TypeScript-side type generation for the extended object shapes remains out of scope (matches J.h's posture — frontend consumes extras as untyped JSON).
- Cross-field validators inside an object (e.g. "if `verified` is false, `doi` must be empty") remain deferred; would require the Python-hook escape that J.h already left for a future story.

## [0.73.0] - 2026-05-21

Phase-J close-out release bundling J.m.6, J.m.7, J.m.8, J.n, and J.o. Highest-impact change is J.o (new Dependabot automation), an improvement; the rest are documentation, a template-internal dependency rebrand, and architectural-principle additions to the canonical quizazz consumer spec.

### Added

- **Dependabot configuration** (Story J.o) — new [.github/dependabot.yml](.github/dependabot.yml) wires weekly grouped patch+minor PRs across three ecosystems: `pip` (root `pyproject.toml` + `requirements-dev.txt`), `npm` (`src/learningfoundry/sveltekit_template/` template), `github-actions` (`.github/workflows/`). Security advisories file PRs immediately, independent of the weekly schedule. `@types/node` `version-update:semver-major` is explicitly ignored (active-LTS pin). New `## Maintenance` section in [README.md](README.md) documents the cadence and the LTS-pin exception.
- **Author guide — "Embedding a quizazz assessment"** (Story J.m.8) — new README subsection under **Pedagogical authoring** covering install prereqs (`learningfoundry[quizazz]`), two embedding shapes (content-block-level `type: assessment` and module-level `assessments[]`), a worked-example YAML, what the learner sees at runtime, optional `pass_threshold` gating, and three common gotchas. Cross-links to quizazz's own [README](docs/specs/quizazz/README.md) and [features.md](docs/specs/quizazz/features.md) for the canonical assessment-YAML schema; deliberately does not duplicate the vendor's schema docs. Light cross-link parentheticals added at the existing content-block YAML examples ([README.md:233](README.md#L233), [:702](README.md#L702)). One-sentence pointer added at [features.md FR-5](docs/specs/features.md#L370).
- **RR-1b: Prop and Event Relabel** (Story J.m.6) — new architectural-principle section in [consumer-dependency-spec.md](docs/specs/quizazz/consumer-dependency-spec.md), inserted immediately after RR-1a. Names `<AssessmentBlock>` as the **single TypeScript-side translation surface** between learningfoundry-domain props/events and quizazz's vendor surface — symmetric to RR-1a (`QuizazzProvider.compile_assessment()`) on the Python side. Documents current direct-wrapper translation behavior (inbound `assessmentRef → quizRef`, outbound `detail.quizRef → assessmentRef`, internal persistence via `progressRepo.saveAssessmentScore`) and adds forward notes for two deferred items now tracked in `stories.md ## Future`: polymorphic provider dispatch via `manifest.source`, and wrapper upward-re-emit refactor.

### Changed

- **`lucide-svelte@^0.468.0` → `@lucide/svelte@^1.16.0`** (Story J.n) — template-internal rebrand migration. Both `lucide-svelte@0.x` and `lucide-svelte@1.0.1` are deprecated on npm with the recommendation to use the rebranded `@lucide/svelte`. Six import sites migrated to the per-icon canonical form (`import ChevronLeft from '@lucide/svelte/icons/chevron-left'`): [Navigation.svelte](src/learningfoundry/sveltekit_template/src/lib/components/Navigation.svelte), [ResetCourseButton.svelte](src/learningfoundry/sveltekit_template/src/lib/components/ResetCourseButton.svelte), [ModuleList.svelte](src/learningfoundry/sveltekit_template/src/lib/components/ModuleList.svelte), [RecordingPausedBanner.svelte](src/learningfoundry/sveltekit_template/src/lib/components/RecordingPausedBanner.svelte), [LockedLessonPlaceholder.svelte](src/learningfoundry/sveltekit_template/src/lib/components/LockedLessonPlaceholder.svelte), [ProgressDashboard.svelte](src/learningfoundry/sveltekit_template/src/lib/components/ProgressDashboard.svelte). No runtime-API change for the generated SvelteKit app; icons render identically. `pnpm-lock.yaml` regenerated; `lucide-svelte` no longer appears in the produced bundle.
- **`consumer-dependency-spec.md` — applied vendor-pushback recommendations** (Story J.m.6) — five structural edits to [consumer-dependency-spec.md](docs/specs/quizazz/consumer-dependency-spec.md) per [vendor-pushback-recommendations.md](docs/specs/quizazz/vendor-pushback-recommendations.md): BR-1 docstring noun "compiled **quiz** manifest" → "compiled **assessment** manifest"; `AssessmentCompleteEvent` event-detail field `quizRef` → `assessmentRef`; Data Flow Summary runtime block rewritten to reflect post-J.m.5 `<AssessmentBlock>` mount point; Package Distribution heading scoped to "(quizazz provider)" with a parent-rule note; Versioning and Compatibility section reframed as the `quizazz` provider's specific application of the general manifest-as-versioning-boundary rule. Vendor surface (`<QuizBlock>`, `quizRef` vendor prop, `quizName` wire key, `QuizazzProvider`, `compile_assessment`, etc.) preserved per project-essentials.
- **Documentation sweep for residual `quiz...` references** (Story J.m.7) — 16 substitutions across [README.md](README.md) (7), [docs/specs/nbfoundry/dependency-spec.md](docs/specs/nbfoundry/dependency-spec.md) (4), [docs/specs/phase-j-pedagogical-authoring-plan.md](docs/specs/phase-j-pedagogical-authoring-plan.md) (1), and [docs/specs/concept.md](docs/specs/concept.md) (4) catching consumer-side prose up to identifiers J.m.2/J.m.3/J.m.4/J.m.5 renamed in code. The 4 J.i-preserved problem-space "quiz platforms" mentions in `concept.md` are deliberately untouched.

### Notes

- **Two recommendations from quizazz's vendor pushback are deliberately deferred** to a future story when triggers materialize, with forward notes in RR-1b and dedicated entries in `stories.md ## Future`:
  - **Polymorphic `<AssessmentBlock>` provider dispatch** — wrapper is currently a direct import of `<QuizBlock>`; once a second `AssessmentProvider` materializes, dispatch will key off `manifest.source`. Building one-branch dispatch logic pre-1.0 with a single provider would be speculative scaffolding.
  - **Wrapper upward-re-emit refactor** — wrapper currently persists internally and fires a no-arg `onassessmentcomplete?.()` upward. Quizazz's recommendation envisions re-emitting a typed `AssessmentCompleteEvent` payload upward and letting the consumer own persistence. Pre-1.0 with one consumer, the inversion adds two footguns (silent score loss if a future consumer forgets to wire persistence; async-ordering for downstream UI) with no current benefit. The current no-arg callback shape is forward-compatible with adding a typed parameter when a second consumer materializes (preview route, authoring sandbox, alternate persistence backend).
- Story under-counted catches across the release: J.m.7 caught the README:233 comment ("Quiz block" → "Assessment block"); J.m.8 caught the Overview bullet at README:35 ("Quiz" → "Assessment"); J.n caught four additional `lucide-svelte` per-icon import sites the story body had not enumerated. Each is recorded in the corresponding story's task list.
- No JSON-contract change, no DDL change, no Python provider/protocol change in this release. The Python and SvelteKit-frontend runtime APIs are identical to v0.72.2.
- pnpm install reports `lucide-svelte@0.563.0` as a *transitive* sub-dependency (some other package pulls it in). This is out of scope for J.n (which targeted the direct dependency only) — the transitive lives under `.pnpm/` and does not reach the produced bundle.

## [0.72.2] - 2026-05-21

### Changed

- **Local `<QuizBlock>` adapter renamed to `<AssessmentBlock>`** (Story J.m.5). [`src/learningfoundry/sveltekit_template/src/lib/components/QuizBlock.svelte`](src/learningfoundry/sveltekit_template/src/lib/components/QuizBlock.svelte) → `AssessmentBlock.svelte` (via `git mv`, history preserved); same for the colocated test file `QuizBlock.test.ts` → `AssessmentBlock.test.ts`. Component header comment refreshed to describe the post-rename role ("learningfoundry's `<AssessmentBlock>` wrapper around the vendor `<QuizBlock>` from `@pointmatic/quizazz`").
- **Wrapper prop `quizRef` → `assessmentRef`** on the local `<AssessmentBlock>`. The wrapper forwards the value to the vendor as `quizRef={assessmentRef}` so the vendor surface stays in vendor terminology while LF callers use LF terminology. `ContentBlock.svelte` updated accordingly: `<QuizBlock ... quizRef={block.ref ?? ''} ... />` → `<AssessmentBlock ... assessmentRef={block.ref ?? ''} ... />`.
- **`LessonView.svelte` comment** updated: "Score already persisted by QuizBlock" → "Score already persisted by AssessmentBlock".
- **Test suite renames** in [`AssessmentBlock.test.ts`](src/learningfoundry/sveltekit_template/src/lib/components/AssessmentBlock.test.ts): `import QuizBlock from './QuizBlock.svelte'` → `import AssessmentBlock from './AssessmentBlock.svelte'`; the four `render(QuizBlock, ...)` calls → `render(AssessmentBlock, ...)`; the four test props `quizRef:` → `assessmentRef:`; `describe('QuizBlock adapter — vendor integration boundary', ...)` → `describe('AssessmentBlock adapter — vendor integration boundary', ...)`. Docblock extended with J.m.5 note.

### Notes

- **Vendor surface preserved** per `project-essentials.md`: the vendor import `import { QuizBlock as VendorQuizBlock } from '@pointmatic/quizazz'` is unchanged; the vendor's `quizRef` prop on `<VendorQuizBlock>` is unchanged (the wrapper forwards `assessmentRef` to it under the vendor's name); the `QuizCompleteDetail` interface mirroring the vendor's event shape (including its `quizRef` field) is unchanged; the vendor-stub mock-object key `{ QuizBlock: VendorQuizBlockStub }` is unchanged (matches the vendor's literal export name).
- Final code-side rename in the J.m cluster. The doc sweep for residual `quiz...` prose references follows in J.m.7; quizazz vendor-pushback recommendations apply in J.m.6.
- No Python changes; no JSON-contract changes; no DDL changes; test count unchanged (4 wrapper tests pass with renamed identifiers).

## [0.72.1] - 2026-05-20

### Changed

- **`QuizScore` TS interface → `AssessmentScore`** (Story J.m.4). Field `quizRef: string` → `assessmentRef: string`. `ModuleProgress.preAssessment` / `postAssessment` references updated.
- **`progress.ts` repo methods renamed:** `saveQuizScore` → `saveAssessmentScore` (takes `Omit<AssessmentScore, 'completedAt'>`); `getQuizScore(quizRef)` → `getAssessmentScore(assessmentRef)`. SQL queries rewritten to use `assessment_scores` / `assessment_ref`. `resetProgress()` transaction now does `DELETE FROM assessment_scores`.
- **Svelte component handlers + callback props renamed:**
  - `LessonView.svelte`: `handleQuizComplete(score: QuizScore)` → `handleAssessmentComplete(score: AssessmentScore)`; callback prop on `<ContentBlock>` `onquizcomplete={...}` → `onassessmentcomplete={...}`.
  - `ContentBlock.svelte`: `onquizcomplete?: (score: QuizScore) => void` callback prop → `onassessmentcomplete?: (score: AssessmentScore) => void`; the prop forwarded to `<QuizBlock>` (the local adapter) is now `onassessmentcomplete`.
  - `ProgressDashboard.svelte`: `quizScores?: Record<string, QuizScore>` prop → `assessmentScores?: Record<string, AssessmentScore>`.
  - `QuizBlock.svelte` (adapter): outbound callback `onquizcomplete?: () => void` → `onassessmentcomplete?: () => void`; `handleComplete()` now builds an `AssessmentScore` (with `assessmentRef: detail.quizRef`) and calls `progressRepo.saveAssessmentScore(score)`. The inbound vendor event's `quizRef` field is preserved (vendor surface — `QuizCompleteDetail.quizRef` stays). The file is the precise boundary where vendor `quizRef` becomes our `assessmentRef`.
- **DDL migration in `database.ts`:** SQLite table `quiz_scores` (with column `quiz_ref`) replaced by `assessment_scores` (with column `assessment_ref`). The DDL block now starts with `DROP TABLE IF EXISTS quiz_scores;` then `CREATE TABLE IF NOT EXISTS assessment_scores (...)`. Idempotent: no-op on fresh DBs and on already-migrated DBs.

### Added

- **Migration smoke test** in [`src/learningfoundry/sveltekit_template/src/lib/db/database.test.ts`](src/learningfoundry/sveltekit_template/src/lib/db/database.test.ts): new `describe` block (4 cases) seeds a pre-J.m.4 IDB blob (legacy `quiz_scores` table populated, no `assessment_scores`) and asserts that next `Database.getDb()` (a) drops the legacy table, (b) creates `assessment_scores` empty, (c) preserves `lesson_progress` + `exercise_status` rows, (d) is idempotent on re-init with persisted post-migration data.

### Removed (BREAKING)

- **In-browser SQLite `quiz_scores` table** — dropped on next `Database.getDb()` after upgrade. **Learner progress in the scores track is permanently lost on upgrade** (per J.i decision; pre-1.0). `lesson_progress` and `exercise_status` are unaffected.
- **TS exports** `QuizScore` (and its `quizRef` field) — use `AssessmentScore` with `assessmentRef`.
- **Repo methods** `progressRepo.saveQuizScore` / `progressRepo.getQuizScore` — use `saveAssessmentScore` / `getAssessmentScore`.
- **Callback props** `onquizcomplete` on `<ContentBlock>` and on the local `<QuizBlock>` adapter — use `onassessmentcomplete`.

### Notes

- Vendor surface preserved per `project-essentials.md`: the local `QuizBlock.svelte` file keeps its filename (mirrors `@pointmatic/quizazz`'s `<QuizBlock>` export); the `quizRef` prop on the vendor component stays; the internal `QuizCompleteDetail.quizRef` event-detail field stays (it mirrors quizazz's emitted event shape). The boundary where vendor `quizRef` becomes learningfoundry `assessmentRef` is the adapter's `handleComplete()`.
- No Python changes; no JSON-contract changes; no `curriculum.json` shape change in this release.
- Story under-counted (re-recurring J.m.2 lesson): also caught and renamed `recordQuizScore` mock-only key in `src/routes/[module]/[lesson]/page.test.ts` → `recordAssessmentScore`; updated the J.m.1 `QuizBlock.test.ts` mock target (`saveQuizScore` → `saveAssessmentScore`), the persisted-field assertion (`quizRef` → `assessmentRef`), and the three `onquizcomplete` test props (now `onassessmentcomplete`).

## [0.72.0] - 2026-05-19

### Changed

- **Pydantic `QuizBlock` → `AssessmentBlock`** (Story J.m.3). [`schema_v1.py`](src/learningfoundry/schema_v1.py) renames the content-block class and its discriminator literal from `type: Literal["quiz"]` → `type: Literal["assessment"]`. `ContentBlock` union updated. `resolver.py` imports, `isinstance` check, and emitted `ResolvedContentBlock.type` literal all updated.
- **TypeScript manifest types renamed** in [`sveltekit_template/src/lib/types/index.ts`](src/learningfoundry/sveltekit_template/src/lib/types/index.ts): `QuizManifest` → `AssessmentManifest`, `QuizQuestion` → `AssessmentQuestion`, `QuizAnswer` → `AssessmentAnswer`. Field `quizName` inside the manifest renamed to `assessmentName`. `ContentBlockType` literal union: `'quiz'` → `'assessment'`. `AssessmentDefinition.content` type updated.
- **`ContentBlock.svelte` discriminator branch:** `{:else if block.type === 'quiz'}` → `'assessment'`; `QuizManifest` casts → `AssessmentManifest`.
- **Local adapter `QuizBlock.svelte`** updated: `manifest: QuizManifest` prop type → `AssessmentManifest`; comment refreshed to note the relabel handoff.
- **`QuizazzProvider.compile_assessment()` now implements the RR-1a wire-format relabel** (`integrations/quizazz.py`): after calling `quizazz.compile_assessment`, rename `quizName` → `assessmentName` in-place before returning. Idempotent (if `assessmentName` is already present, leave it). Closes the latent bug where the contract was documented in three places but the code was a pass-through.
- **Curriculum YAML fixture** `tests/fixtures/valid-curriculum.yml`: discriminator + ref filename updated.

### Added

- **Wire-format relabel tests** in [`tests/test_integrations/test_quizazz.py`](tests/test_integrations/test_quizazz.py): new `TestWireFormatRelabel` class (5 cases) pins the RR-1a contract — `quizName` → `assessmentName`, other fields pass through, idempotent when already relabeled, no-op when neither key is present, conservative when both are present.

### Removed (BREAKING)

- **YAML discriminator `type: quiz`** — fails to parse with a Pydantic `ValidationError`. Curricula authored against pre-v0.72.0 must update to `type: assessment`. No alias.
- **`QuizBlock` Pydantic import** — `from learningfoundry.schema_v1 import QuizBlock` no longer resolves. Use `AssessmentBlock`.
- **TypeScript exports** `QuizManifest`, `QuizQuestion`, `QuizAnswer` — replaced by `AssessmentManifest`, `AssessmentQuestion`, `AssessmentAnswer`.
- **Wire-format field `quizName`** — emitted `curriculum.json` no longer contains this key; downstream consumers must read `assessmentName`. (Quizazz still emits `quizName` on its vendor wire format; the adapter relabels at the boundary.)

### Notes

- `QuizScore` TS type and the SQLite `quiz_scores` table remain unchanged in this release — those are J.m.4 (frontend persistence rename with data-loss DB migration).
- The vendor surface is preserved per `project-essentials.md`: the local Svelte component file is still named `QuizBlock.svelte` (mirroring `@pointmatic/quizazz`'s `<QuizBlock>` export); the `quizRef` prop name on the vendor component stays; `QuizCompleteDetail.quizRef` event field stays (it mirrors the vendor event payload).
- Internal helper `vi.hoisted` typing in `QuizBlock.test.ts` adjusted to bypass `svelte-check`'s strict indexed-access rule.

## [0.71.0] - 2026-05-19

### Changed

- **`QuizProvider` Protocol → `AssessmentProvider`** (Story J.m.2). The provider Protocol in [`src/learningfoundry/integrations/protocols.py`](src/learningfoundry/integrations/protocols.py) is renamed to match learningfoundry's "Assessment" domain vocabulary. `QuizazzProvider` adapter class name preserved (vendor boundary).
- **`quiz_provider=` keyword → `assessment_provider=`** across `pipeline.build()`, `pipeline.validate()`, `pipeline.preview()`, and `resolver.resolve_curriculum()` plus all internal helpers in `resolver.py`. Test sites updated in `test_resolver.py`, `test_pipeline.py`, `test_edge_cases.py`, `test_pedagogical_authoring_smoke.py`, `test_smoke_sveltekit.py`.
- **Renamed:** `tests/test_phase_j_smoke.py` → `tests/test_pedagogical_authoring_smoke.py`; `tests/fixtures/phase-j-curriculum.yml` → `tests/fixtures/pedagogical-authoring-curriculum.yml`; `tests/fixtures/phase-j-content/` → `tests/fixtures/pedagogical-authoring-content/`. The test exercises the *pedagogical-authoring* feature cluster (meta, hooks, tutorial directives, three-position assessments, duration aggregation); "Phase J" was workflow-internal vocabulary that won't outlive the phase. Git history preserved via `git mv`. Story J.g attribution kept in the test docstring as historical lineage.
- **Docstrings:** "Override for quiz resolution" → "Override for assessment resolution"; module + class docstrings in [`integrations/quizazz.py`](src/learningfoundry/integrations/quizazz.py) updated to reference `AssessmentProvider`.

### Removed (BREAKING)

- **`QuizProvider` import** — `from learningfoundry.integrations.protocols import QuizProvider` no longer resolves. Use `AssessmentProvider` instead. Pre-1.0 break; no alias.
- **`quiz_provider=` keyword argument** on the public `pipeline.build()` / `pipeline.validate()` / `pipeline.preview()` API. Callers passing `quiz_provider=...` will fail with a `TypeError` for unexpected keyword. Switch to `assessment_provider=...`.

### Notes

- Internal-only rename; no JSON contract change, no DB change, no TS change. The wire-format relabel (`quizName` → `assessmentName`) is scheduled for J.m.3; SQLite `quiz_scores` rename for J.m.4.
- `QuizBlock` Pydantic class and YAML `type: quiz` discriminator **unchanged** in this release — both land in J.m.3.

## [0.70.0] - 2026-05-19

### Added

- **Live `@pointmatic/quizazz` SvelteKit integration** (Story J.m.1). Assessment content blocks in generated SvelteKit apps now render the real vendor quiz UI from [`@pointmatic/quizazz@^1.3.1`](https://www.npmjs.com/package/@pointmatic/quizazz) instead of the placeholder banner shipped pre-v0.70.0. Vendor-side score events translate to learningfoundry's `QuizScore` and persist to the in-browser SQLite `quiz_scores` table; pass-threshold gating remains in the adapter.
- **Component test:** [`src/learningfoundry/sveltekit_template/src/lib/components/QuizBlock.test.ts`](src/learningfoundry/sveltekit_template/src/lib/components/QuizBlock.test.ts) — 4 cases pinning the adapter contract (manifest/quizRef prop forwarding, vendor `complete` event translation to `QuizScore`, `progressRepo.saveQuizScore` persistence, pass-threshold gating, zero-question edge case). Vendor component is stubbed via `vi.mock` so the test exercises only the adapter's translation logic.

### Changed

- **`src/learningfoundry/sveltekit_template/src/lib/components/QuizBlock.svelte`** — adapter now imports `QuizBlock as VendorQuizBlock` from `@pointmatic/quizazz` and renders it in place of the prior `<PlaceholderBlock>` fallback. Manifest shape is cast at the prop boundary (`as never`) to bridge the structural gap between learningfoundry's pass-through type and the vendor's narrower type — runtime shapes are identical since both describe quizazz's `compile_assessment` output. File header comment updated to describe the file's role as an adapter (no longer "placeholder pending @pointmatic/quizazz").
- **`src/learningfoundry/sveltekit_template/src/routes/+layout.svelte`** — root layout now imports `@pointmatic/quizazz/styles.css` alongside the existing `app.css` import, per `dependency-spec.md` RR-4 (vendor host setup).
- **`src/learningfoundry/sveltekit_template/package.json`** — added `@pointmatic/quizazz: ^1.3.1` to `dependencies`. The npm package is now an actual runtime dependency of the generated SvelteKit app, not an aspirational reference.

### Notes

- The local `QuizBlock.svelte` adapter file is kept (not deleted) — it preserves the score-persistence + pass-threshold + event-dispatch protocol that `ContentBlock.svelte` calls. Vendor surface (`quizRef` prop, `QuizCompleteDetail.quizRef` event field, internal vendor types `quizName`, `QuizManifest`) preserved per `project-essentials.md` "Vendor terminology stops at the vendor boundary."
- `PlaceholderBlock.svelte` is unchanged — still used for other content-block stubs (`NbfoundryStub`, `D3foundryStub`).
- The remaining `Quiz*` → `Assessment*` internal renames (`QuizProvider` Protocol, `quiz_provider` parameter, Pydantic `QuizBlock`, YAML `type: quiz` discriminator, TS `QuizManifest`/`QuizScore`, SQLite `quiz_scores` table) are scheduled across stories J.m.2 / J.m.3 / J.m.4 / J.m.5.

## [0.69.1] - 2026-05-18

### Added

- **`CurriculumMeta`** — new optional `meta:` block on the top-level `curriculum:` mapping (Story J.h). Mirrors the existing `LessonMeta` / `ModuleMeta` shape with three declared fields (`target_audience`, `objectives`, `prerequisites`) plus `extra="allow"` so authors can attach curriculum-wide pedagogical context without forcing a schema change. Threaded through the resolver into `curriculum.json`; mirrored in the SvelteKit `Curriculum` TypeScript interface. Rendering is deferred to a later phase, matching the J.a precedent for `ModuleMeta`.
- **Project-specific schema extensions** — opt-in mechanism for tightening the three `meta` blocks' `extra="allow"` posture into strict whitelist-reject validation (Story J.h). When `learningfoundry-schema-extensions.yml` is present next to `curriculum.yml`, learningfoundry synthesizes strict subclasses of `CurriculumMeta` / `ModuleMeta` / `LessonMeta` with project-declared fields appended and `extra` flipped to `forbid`. Motivated by LLM-driven authoring workflows where phantom fields (typos like `prequisites` instead of `prerequisites`) silently pass `extra="allow"` and get lost in the resolved JSON.
- **`--schema-extensions PATH`** CLI flag on `build`, `validate`, and `preview`. Resolution order: CLI flag > `[tool.learningfoundry] schema_extensions = "..."` in `pyproject.toml` next to the curriculum > auto-discovery of `learningfoundry-schema-extensions.yml` next to the curriculum > none (base behaviour preserved).
- **Supported extension field types:** `str`, `int`, `bool`, `list[str]`, `enum` (with `values:` list). Per-field `required: bool` (default `true`) and `default:` (optional — presence makes the field optional regardless of `required`).
- **`SchemaExtensionError`** — new typed exception for missing / malformed / invalid extension files. Mapped to exit code 4 (`EXIT_CONFIG`) in the CLI.
- **New module:** [`src/learningfoundry/schema_extensions.py`](src/learningfoundry/schema_extensions.py) with `SchemaExtensions`, `MetaExtensions`, five discriminated `FieldDef` variants, `build_extended_meta_models`, `build_extended_curriculum_v1`, `load_schema_extensions`.
- **Tests:** [`tests/test_schema_extensions.py`](tests/test_schema_extensions.py) — 45 cases covering base behaviour preservation, strict whitelist rejection, every supported field type, required/default rules, per-model `extra` override, `CurriculumMeta` extension propagation, end-to-end through `parse_curriculum` and `run_validate`, file-path resolution precedence, CLI invocation via Click `CliRunner`, and strict validation of the extension file itself. Plus 6 new `CurriculumMeta` cases in `test_schema_v1.py` and 2 round-trip cases in `test_resolver.py`.
- **Docs:** new "Strict project-specific extensions" subsection in [README.md](README.md) and `CurriculumMeta` entry in the meta reference; new "Project-specific `meta` schema extensions" subsection in [docs/specs/features.md](docs/specs/features.md); new `schema_extensions.py` subsection plus `CurriculumMeta` in the schema overview in [docs/specs/tech-spec.md](docs/specs/tech-spec.md).

### Notes

- Backward compatible: when no extensions file is found, today's `extra="allow"` behaviour is preserved bit-for-bit. No existing curriculum needs to change.
- The mechanism is scoped to `meta` blocks (`CurriculumMeta`, `ModuleMeta`, `LessonMeta`) — `Lesson`, `Module`, `CurriculumDef` themselves stay unconditionally strict. `Hook` extensions are deferred (small surface, no asks).
- A Python-module schema hook (`schema_module = "..."`) is recorded as a possible follow-up if a curriculum ever needs cross-field validators.

## [0.69.0] - 2026-05-08

### Added

- **Sidebar module flow renders assessments at their resolved positions** (Story J.f). [LessonList.svelte](src/learningfoundry/sveltekit_template/src/lib/components/LessonList.svelte) now interleaves assessment rows with lesson rows according to each assessment's `position`: `before_lessons` at the top, `{ before_lesson: <id> }` / `{ after_lesson: <id> }` around the named lesson, `after_lessons` at the bottom. Order in `module.assessments` is the canonical iteration order — the resolver emitted it that way and the component does not re-resolve placement.
- **Role label + pass-threshold annotation on each assessment row.** Role rendered capitalized (`pre` → `Pre Assessment`); `pass_threshold` rendered as a secondary `"70% to pass"` annotation when set. Rows are non-interactive — gating semantics is a future concern.
- **`interleaveModuleFlow`, `capitalizeRole`, `formatPassThreshold`** helpers in [module-list.helpers.ts](src/learningfoundry/sveltekit_template/src/lib/components/module-list.helpers.ts) plus 10 new unit tests in `module-list.test.ts` and 5 new DOM tests in `LessonList.test.ts`.
- [ModuleList.svelte](src/learningfoundry/sveltekit_template/src/lib/components/ModuleList.svelte) now passes `mod.assessments` to `LessonList`.

### Phase J close (Story J.g)

- **Cross-cutting Phase J smoke fixture** at [tests/fixtures/phase-j-curriculum.yml](tests/fixtures/phase-j-curriculum.yml) and [tests/fixtures/phase-j-content/](tests/fixtures/phase-j-content/) exercises every Phase J affordance — lesson + module `meta`, all three tutorial directives, all three assessment roles with mixed positions, and `duration_minutes` aggregation — in a single curriculum. The new [tests/test_phase_j_smoke.py](tests/test_phase_j_smoke.py) (9 cases) pins the composition end-to-end through parse → resolve → generate. Per-feature tests stay narrow; this one is the integration anchor.
- **README "Pedagogical authoring" section** stitches the per-feature docs into a single author-facing story with a worked example covering meta blocks, tutorial directives, and the `assessments[]` array. Includes a migration paragraph for `pre_assessment` / `post_assessment` → `assessments[]` for any external curriculum that pre-dates v0.68.0.
- **features.md FR-2** now has a brief "Phase J: Pedagogical authoring" header tying the J.a–J.f subsections together and pointing at the integration test.

J.g is doc + integration-test only — shares the v0.69.0 release with J.f, no extra version bump.

### Notes

- Defensive belt: a lesson-anchored assessment whose target lesson does not exist is silently dropped at render time. The parser already rejects unknown refs at build time (`Module.validate_assessment_lesson_refs`); this guard ensures the component does not crash if one slips through.
- Mid-lesson assessment placement, gating ("must pass post to advance"), per-role styling beyond label text, and assessment-specific routes remain out of scope.

## [0.68.0] - 2026-05-08

### Removed (BREAKING)

- **`Module.pre_assessment` / `Module.post_assessment`** are gone from the curriculum schema, the resolved-curriculum dataclass, the generated `curriculum.json`, and the SvelteKit `Module` TypeScript interface (Story J.e). No alias, no deprecation warning, no shim — pre-1.0 makes the clean break acceptable. Curriculum YAML authors **must** migrate to the new `assessments[]` array; an unmigrated `pre_assessment` / `post_assessment` field at module level now produces a `ValidationError` from strict-mode Pydantic.
- ProgressDashboard's "Pre-assessment: X/Y" / "Post-assessment: X/Y" inline score rows are gone. The per-learner score data still lives in IndexedDB; a future story rebuilds the score-display UI atop the new shape.

### Added

- **`Module.assessments: list[AssessmentDefinition]`** — generalized array replacing the two-slot pre/post (Story J.e). Each `AssessmentDefinition` carries:
  - `role`: open string (conventional values `pre`, `practice`, `post`, `checkpoint`).
  - `position`: discriminated union — `"before_lessons"` / `"after_lessons"` / `{ before_lesson: <id> }` / `{ after_lesson: <id> }`.
  - `source`, `ref`, optional `pass_threshold`.
- **Parse-time lesson-id validation.** A `model_validator` on `Module` rejects assessments whose `before_lesson` / `after_lesson` ref names a lesson that does not exist in the module, with an error message naming the module id, the assessment role, and the unknown lesson id.
- **Resolver materializes canonical assessment order.** `_resolve_assessments` walks the `assessments` array and emits a `ResolvedAssessment` list in placement order: `before_lessons` first, then for each lesson the `before_lesson` and `after_lesson` anchors, then `after_lessons`. Order is the canonical iteration order; each entry retains its original `position` (serialized as JSON-friendly string or single-key mapping) so the frontend can interleave at render time.
- **TypeScript `AssessmentDefinition` and `AssessmentPosition` types** in [lib/types/index.ts](src/learningfoundry/sveltekit_template/src/lib/types/index.ts).

### Notes

- Frontend rendering of assessments at their resolved positions in the module flow lands in **Story J.f** (v0.69.0). Until then, `module.assessments[]` is plumbed through end-to-end but no UI surfaces it.
- `pass_threshold` is recorded but not enforced in v1 — gating semantics is a future concern that may also touch the progress-DB schema.

## [0.67.1] - 2026-05-08

### Added

- **Build-time lint for unbalanced tutorial-scaffold directives** (Story J.d.2). New [directives.py](src/learningfoundry/directives.py) (`lint_directives`) scans every `text` content block's markdown for `::: worked-example` / `::: faded-example` / `::: independent-practice` opens with no matching `:::` close on its own line, and raises `ContentResolutionError` with the lesson location and the 1-based opening line number. Hooked into [resolver.py](src/learningfoundry/resolver.py) `_resolve_text` after the markdown is read but before image-asset resolution, so authors get a build-time error rather than discovering the problem as a render-time anomaly.
- Lint is conservative by design: only the three known directive names are tracked; unknown names (`::: tip`) pass through untouched, and lines inside fenced code blocks (``` or `~~~`) are skipped so prose that demonstrates the directive syntax isn't mistaken for an actual directive.
- tech-spec.md gained a `directives.py` subsection documenting the lint contract and the TS↔Python coupling on the `KNOWN_DIRECTIVES` list.

## [0.67.0] - 2026-05-08

### Added

- **Tutorial scaffold container directives in lesson markdown** (Story J.d.1). Three named container directives — `::: worked-example`, `::: faded-example`, `::: independent-practice` — recognised by a custom `marked` extension at [markdown-directives.ts](src/learningfoundry/sveltekit_template/src/lib/utils/markdown-directives.ts). Each directive opens with `::: <name>` on its own line and closes with `:::` on its own line; inner content is itself markdown so headings, lists, math, and emphasis nest naturally.
- **CSS for the three directive treatments** in [app.css](src/learningfoundry/sveltekit_template/src/app.css): `lf-directive-worked-example` = filled gray card; `lf-directive-faded-example` = outlined dim card; `lf-directive-independent-practice` = amber-highlighted challenge prompt. Pure CSS so the styles ship in the bundled output regardless of Tailwind content-detection.
- README "Tutorial scaffold directives" section with author-facing examples; features.md FR-3 subsection documenting the rendering contract.

### Notes

- Unknown directive names (e.g. `::: tip`) pass through untouched at render time. The Python-side lint that flags malformed or unknown directive blocks at build time lands in **Story J.d.2** (v0.67.1).
- Static styling only — interactivity (progressive reveal, hint toggles, checkmark affordances) is out of scope.

## [0.66.0] - 2026-05-08

### Added

- **Curriculum-wide aggregate time estimate** (Story J.c). [generator.py](src/learningfoundry/generator.py) sums every lesson's `meta.duration_minutes` and emits the result as `curriculum.total_duration_minutes` at the top level of `curriculum.json`. Lessons without `meta` or without `duration_minutes` are skipped; when no lesson contributes, the field is `null`.
- **Index page renders the estimate above the dashboard** when non-null, formatted as `≈ Xh Ym` (or `≈ Xm` under an hour, `≈ Xh` for whole-hour totals). Hidden entirely when `total_duration_minutes` is `null`. New helper [duration.ts](src/learningfoundry/sveltekit_template/src/lib/utils/duration.ts) (`formatDurationEstimate`) owns the formatting; [+page.svelte](src/learningfoundry/sveltekit_template/src/routes/+page.svelte) renders it.
- TypeScript `Curriculum` interface gained `total_duration_minutes?: number | null` ([lib/types/index.ts](src/learningfoundry/sveltekit_template/src/lib/types/index.ts)).

### Notes

- Per-module aggregation, learner-elapsed-time display, and adaptive estimates from past learner pace remain out of scope (Phase J / J.c).

## [0.65.0] - 2026-05-08

### Added

- **Lesson role chip in the sidebar** (Story J.b). When `lesson.meta.role` is set, [LessonList.svelte](src/learningfoundry/sveltekit_template/src/lib/components/LessonList.svelte) renders a small uppercase chip (e.g. `OPENER`, `PRACTICE`) at the right edge of the lesson row, distinct in styling from the progress glyph and the locked-row indicator. Hidden when `meta.role` is absent.
- **Lesson hook tagline above the title** (Story J.b). When `lesson.meta.hook.tagline` is set, [LessonView.svelte](src/learningfoundry/sveltekit_template/src/lib/components/LessonView.svelte) renders the tagline as a quiet italic line directly above the `<h1>` lesson title. Hidden when absent.
- Test fixture [valid-curriculum.yml](tests/fixtures/valid-curriculum.yml) now exercises lesson and module `meta` end-to-end; smoke test pins the meta-passthrough data contract on the production `build/curriculum.json`.

### Notes

- `hook.image_prompt` is intentionally not rendered — no consumer exists pre image-generation pipeline.
- Module-level `meta.theme` rendering on the module index and `meta.duration_minutes` aggregation land in subsequent Phase J stories.

## [0.64.0] - 2026-05-08

### Added

- **Pedagogical metadata on lessons and modules** (Story J.a — Phase J kickoff). New `Hook`, `LessonMeta`, and `ModuleMeta` Pydantic models in [schema_v1.py](src/learningfoundry/schema_v1.py); optional `meta` fields on `Lesson` and `Module`. `LessonMeta` carries `role`, `hook` (`tagline` + optional `image_prompt`), `introduces`, `reinforces`, and `duration_minutes`; `ModuleMeta` carries `theme`, `big_problem`, `objectives`, `experiential_summary`, and `target_audience`. All meta models use `extra="allow"` so authors can attach genre-specific fields without schema churn.
- **`meta` propagated verbatim into `curriculum.json`.** [resolver.py](src/learningfoundry/resolver.py) carries the resolved meta dicts on `ResolvedLesson` and `ResolvedModule`; [generator.py](src/learningfoundry/generator.py) emits them through `dataclasses.asdict`. Absent meta serializes as `"meta": null`.
- **TypeScript mirrors** for `Hook`, `LessonMeta`, and `ModuleMeta` in [lib/types/index.ts](src/learningfoundry/sveltekit_template/src/lib/types/index.ts).

### Notes

- No frontend rendering of `meta` yet — surfacing of `meta.role` and `meta.hook.tagline` lands in Story J.b; `duration_minutes` aggregation lands in Story J.c.

## [0.63.0] - 2026-05-03

### Added

- **`WasmAssetMissingError` is now visible to the learner** (Story I.bb). When `Database.getDb()` rejects because `/sql-wasm.wasm` is unavailable, a persistent layout-level banner appears above the main content area: "Progress recording is paused. Your activity in this session will not be saved. Try refreshing to retry." with a Refresh CTA that calls `location.reload()`. Pre-fix the failure was CLI-log-only — the learner saw checkmarks fail to land, no in-progress icons, no module advancement, and no UI signal explaining why. Story I.aa hardened the asset pipeline so this should be rare in deployed apps; Story I.bb closes the loop on what the learner actually sees if it ever recurs (asset-pipeline regression, deploy misconfiguration, browser cache poisoning, network partition).
- New [src/lib/stores/db-init.ts](src/learningfoundry/sveltekit_template/src/lib/stores/db-init.ts) — `dbInit` writable store (`pending` | `ready` | `wasm-missing` | `failed`) plus an idempotent `initializeDatabase()` that drives the store from a one-shot `database.getDb()` call wired into `+layout.svelte`. Single-signal layout-level surfacing (option (c) from the story design notes), so per-write rejections don't have to handle the case independently.
- New [RecordingPausedBanner.svelte](src/learningfoundry/sveltekit_template/src/lib/components/RecordingPausedBanner.svelte) renders only when `dbInit` is in `wasm-missing` state. AlertTriangle icon, amber palette, accessible `role="status"` + `aria-live="polite"`.

### Changed

- **`progress.ts` swallows `WasmAssetMissingError` at the repository boundary.** Once the layout banner is up, per-call rejections are an information duplicate that every UI call site would have to defend against. Writes (`markLessonComplete` / `markLessonOpened` / `markLessonInProgress` / `saveQuizScore` / `updateExerciseStatus` / `resetProgress`) resolve as no-ops; reads (`getLessonProgress`, `getQuizScore`) return `null`; `getModuleProgress` returns an empty `not_started` shape so the dashboard renders the empty state instead of an error page. Non-WASM errors still propagate. Module-level doc comment in [progress.ts](src/learningfoundry/sveltekit_template/src/lib/db/progress.ts) documents the rule so a future maintainer doesn't refactor the catches away.
- **`+layout.svelte`** wraps `<main>` in a flex column that hosts the banner above the scrollable content region; main keeps `overflow-y-auto`, banner stays pinned at the top.
- **[features.md](docs/specs/features.md) FR-4** now documents the recording-paused state as a hard requirement (closes the requirements gap Story I.aa identified).

## [0.62.2] - 2026-05-02

### Fixed

- **Dashboard "Start module →" CTA didn't reflect locked state** (Story I.aa.3). [ProgressDashboard.svelte](src/learningfoundry/sveltekit_template/src/lib/components/ProgressDashboard.svelte) rendered the same active-blue button for every non-complete module regardless of whether `locking.sequential` had locked it. Story I.aa.2 caught the click at the lesson route and rendered a placeholder, but the dashboard was still inviting the click. Same anti-pattern as I.aa.2: locking enforcement was in one place (sidebar) and missed at every other entry point. Fix: dashboard now derives `lockedModules` from the same `lockedModuleIds` helper the sidebar uses, and renders a `Locked` indicator (Lucide Lock icon + `text-gray-400` + `aria-disabled="true"`) instead of the action button when a module is locked. The module title also picks up the Lock icon for visual cohesion with the sidebar idiom.

## [0.62.1] - 2026-05-02

### Fixed

- **Locking config silently disabled when `sequential: true` was mis-placed in the YAML** (Story I.aa.2). Repro: a curriculum YAML with `sequential: true` written one indent level too high (directly under `curriculum:` instead of nested under `curriculum.locking:`) silently parsed with `locking.sequential = false`, so every module was freely expandable, every lesson freely openable, and no lock icon appeared in the sidebar. Pydantic's default `extra='ignore'` ate the unknown field without any warning. Compounded by [+page.svelte](src/learningfoundry/sveltekit_template/src/routes/[module]/[lesson]/+page.svelte) having no locking guard at all — even with the schema fixed, typing or bookmarking a locked-lesson URL would have bypassed the sidebar's enforcement entirely.

### Changed

- **Curriculum schema is now strict.** New `StrictModel` base class in [schema_v1.py](src/learningfoundry/schema_v1.py) sets `model_config = ConfigDict(extra='forbid')`. Every schema model (`CurriculumDef`, `Module`, `Lesson`, `LockingConfig`, `CurriculumV1`, `*Block` types, `AssessmentRef`) inherits from it. A misplaced or typo'd field anywhere in the YAML now produces a `ValidationError` with a JSON-pointer path to the offending field — e.g. `curriculum.sequential — Extra inputs are not permitted`. Breaking change for any curriculum YAML that contained benign extra fields; the project ships only the test fixtures and one user's curriculum, none of which use extras.

### Added

- **Lesson-route locking failsafe** (Story I.aa.2). [+page.svelte](src/learningfoundry/sveltekit_template/src/routes/[module]/[lesson]/+page.svelte) now derives `isLocked` from the same `isModuleLocked` / `isLessonLocked` helpers the sidebar uses, and renders a new [LockedLessonPlaceholder.svelte](src/learningfoundry/sveltekit_template/src/lib/components/LockedLessonPlaceholder.svelte) (lock icon + module/lesson titles + "Complete X to unlock this lesson" + Return-to-dashboard CTA) when the requested URL points at a locked lesson. The `navigateTo` side-effect is guarded by `!isLocked` so a locked-URL load doesn't write `currentPosition` and therefore doesn't highlight the gated module in the sidebar.

## [0.62.0] - 2026-05-02

### Fixed

- **Course-title click on the dashboard didn't collapse a manually-expanded module** (Story I.aa.1). Repro: on the dashboard with no lesson active (`currentPosition === null`), expand a module by clicking its header, then click the course title — pre-fix, the module stayed expanded. Story I.y had only fixed the path where a lesson *was* active. Root cause: [layout.helpers.ts](src/learningfoundry/sveltekit_template/src/routes/layout.helpers.ts) `clearActivePosition` set `currentPosition` to null and relied on `ModuleList`'s auto-expand `$effect` to observe the change and collapse the module. But Svelte 5's `$store` deref maintains an internal `$state` for the store and updates it via `Object.is`-equality — so a `set(null)` on an already-null `currentPosition` produces no change to the dependent effect, and the effect never re-ran. The course-title-click reset path simply did not fire when the learner started from the dashboard.

### Changed

- **`expandedModuleId` lifted from component-local state to a Svelte writable.** `ModuleList`'s previously-local `let expandedModuleId = $state<string | null>(null)` is now exported as `writable<string | null>(null)` from [stores/curriculum.ts](src/learningfoundry/sveltekit_template/src/lib/stores/curriculum.ts), so external callers can collapse modules directly without going through the `$effect`. `clearActivePosition` now resets two stores: `currentPosition` (unchanged from Story I.y) and `expandedModuleId` (new). The auto-expand `$effect` keeps its original 2-arg `computeAutoExpand` signature and continues to handle auto-expand-on-navigation and FR-P14 Finish; it just stops being a side-channel for the course-title-click case. `lastAutoExpandedModuleId` stays component-local — it has no external consumer.

## [0.61.0] - 2026-05-02

### Fixed

- **Recording silently broken on every `learningfoundry preview` after the first** (Story I.aa). The CLI logged `[404] GET /sql-wasm.wasm`; the UI showed no progress checkmarks, no in-progress icons, no module/lesson advancement, because every lesson event / quiz score / exercise status write was rejecting at `Database.getDb()` and the rejection was never surfaced. Two fragile asset-supply channels were *both* expected to keep `output_dir/static/sql-wasm.wasm` populated, and they cancelled each other: (1) `_atomic_copy` rebuilt `static/` from a template that doesn't ship the wasm (gitignored), erasing any existing copy in `output_dir/static/`, while (2) the `pnpm postinstall` hook that *would* have re-provisioned the file only ran when `pipeline.run_preview` chose to actually `pnpm install` — which it skips on `DepState.UNCHANGED`, i.e. every iterate-on-content rebuild. The `Database.getDb()` rejection on the missing wasm was an opaque `Error` from sql.js's WebAssembly fetch path, indistinguishable to UI callers from "no progress yet", which is why the only signal was the 404 in the CLI logs.

### Changed

- **Python is now the single owner of `static/sql-wasm.wasm`.** New [pipeline.py](src/learningfoundry/pipeline.py) helper `_ensure_sql_wasm(output_dir)` is called unconditionally from `run_preview` after the install gate; it copies `output_dir/node_modules/sql.js/dist/sql-wasm.wasm` → `output_dir/static/sql-wasm.wasm` whenever the destination is missing or content-stale, and raises `GenerationError` with a clear message if the source is absent (converts a runtime 404 into a build-time error). `static/sql-wasm.wasm` also added to [generator.py](src/learningfoundry/generator.py) `_PRESERVED_PATHS` as belt-and-braces. The pnpm `postinstall` hook in [package.json](src/learningfoundry/sveltekit_template/package.json) is removed — two-ways-of-doing-the-same-thing was how this bug got nasty.

### Added

- **Typed DB-init failure: `WasmAssetMissingError`.** [database.ts](src/learningfoundry/sveltekit_template/src/lib/db/database.ts) now exports a typed error class and the `#initSqlJs` path does an explicit HEAD-fetch precheck against `/sql-wasm.wasm` before delegating to `initSqlJs`. Bypasses sql.js's module-level wasm caching (which previously masked 404s as silently rejected progress writes) so a missing asset surfaces as `instanceof WasmAssetMissingError` for any consumer that wants to render a recoverable banner. UI surfacing of the error is deferred to a follow-up story.

## [0.60.0] - 2026-05-02

### Fixed

- **3 pre-existing e2e failures rooted in the curriculum fixture never being planted before `pnpm build`** (Story I.z). [navigation.spec.ts:10](src/learningfoundry/sveltekit_template/e2e/navigation.spec.ts#L10) "sidebar lesson click updates URL", [navigation.spec.ts:24](src/learningfoundry/sveltekit_template/e2e/navigation.spec.ts#L24) "dashboard 'Start module' deep-links into a lesson", and [video.spec.ts:12](src/learningfoundry/sveltekit_template/e2e/video.spec.ts#L12) "lesson page renders at most one YouTube iframe per video block" had been failing on clean `main` since at least v0.55.0 — flagged but deferred in Stories I.v through I.y. Root cause was that the template's `static/` directory has no `curriculum.json` (the fixture lives at [e2e/fixtures/curriculum.json](src/learningfoundry/sveltekit_template/e2e/fixtures/curriculum.json) but was never being copied into `static/` before `pnpm build`); preview therefore served a `build/` that 404'd on every `/curriculum.json` request, the curriculum readable's `loadCurriculum()` rejected, and `ModuleList`'s `{#if $modules.length && $curriculum}` gate stayed false. Three tests timed out on `aside nav button` selectors that never matched. Fix: [playwright.config.ts](src/learningfoundry/sveltekit_template/playwright.config.ts) `webServer.command` now chains `cp e2e/fixtures/curriculum.json static/curriculum.json && pnpm build && pnpm preview ...` so the fixture is in place before the build, and a new [e2e/global-teardown.ts](src/learningfoundry/sveltekit_template/e2e/global-teardown.ts) removes the planted file after the suite so `static/` stays clean for `pnpm dev`. (The first attempt used Playwright's `globalSetup` for the copy, which silently failed because Playwright runs `webServer` *before* `globalSetup`; documented inline so a future maintainer doesn't refactor back to that shape.)

### Changed

- `webServer.timeout` in [playwright.config.ts](src/learningfoundry/sveltekit_template/playwright.config.ts) bumped from 60s to 120s to accommodate the chained build step. The full e2e suite now runs in 12.6s on a clean checkout (was ~60s with the 3 timeouts dominating the wall clock); local-iteration time should improve as well.

## [0.59.0] - 2026-05-02

### Fixed

- **Sidebar still showed expanded module + highlighted lesson when the learner clicked the course-title link to return to the dashboard** (Story I.y). The course-title `<a href="/">` in [+layout.svelte](src/learningfoundry/sveltekit_template/src/routes/+layout.svelte) had no click handler, so navigating to `/` left `currentPosition` populated; `ModuleList`'s active-highlight CSS kept the parent module marked active and the auto-expand `$effect` saw no change so didn't collapse. The cascade for collapsing on a null `currentPosition` was already in place — `ResetCourseButton` and the FR-P14 Finish button both clear it for the same reason, and `computeAutoExpand(null, lastAutoExpandedModuleId !== null)` already returns the collapse instruction — the bug was that the title link never triggered the clear. Fix: new [layout.helpers.ts](src/learningfoundry/sveltekit_template/src/routes/layout.helpers.ts) exports `clearActivePosition()` (one line, `currentPosition.set(null)`); the title link's `onclick` is wired to it. Two anti-regression cases added to [layout.test.ts](src/learningfoundry/sveltekit_template/src/routes/layout.test.ts) — populated→null and null→null no-op.

## [0.58.0] - 2026-05-02

### Added

- **Per-user progress data partitioning** (Story I.x). The sql.js database is now persisted under an IDB key of `db:${userId}` instead of the previous unkeyed `db`. `userId` is a UUID v4 stored in `localStorage` under `learningfoundry-user-id`, generated on first visit. New [user-id.ts](src/learningfoundry/sveltekit_template/src/lib/db/user-id.ts) exposes `getUserId(): Promise<string>`; the read-or-create is wrapped in `navigator.locks.request('lf-user-id-bootstrap', { mode: 'exclusive' }, ...)` so two simultaneously-loading tabs on a fresh browser converge on a single UUID rather than racing to generate two competing values. Browsers without Web Locks (Safari < 15.4) fall back to an unlocked generate-and-store — race window is small enough to be acceptable.
- **One-shot legacy IDB key migration** (Story I.x). On first `Database.getDb()` call for any userId, pre-v0.58.0 bytes under the legacy `db` IDB record are adopted under `db:${userId}` (only if the per-user record doesn't already exist) and the legacy key is deleted. Idempotent — second call is a no-op. This claims existing pre-upgrade progress for whichever local UUID is generated on first post-upgrade load (acceptable because there was no concept of "different users on this browser" pre-userId).
- **Tests for the partition + bootstrap + migration paths** (Story I.x). [user-id.test.ts](src/learningfoundry/sveltekit_template/src/lib/db/user-id.test.ts) covers fresh-localStorage UUID generation, no-rotation on subsequent calls, and the two-parallel-callers convergence via a fake `navigator.locks.request` shim that simulates real exclusive serialisation. [database.test.ts](src/learningfoundry/sveltekit_template/src/lib/db/database.test.ts) gains "different userIds don't see each other's rows" partition-isolation cases and a migration test that pre-writes raw bytes under the legacy `db` key, instantiates a `new Database('user-x')`, and asserts the migrated rows arrive while the legacy key is removed.

### Changed

- **`Database` constructor signature** (Story I.x). `new Database()` now optionally accepts a `userId: string`. Tests pass an explicit value for partition isolation (`new Database('user-a')`); production code omits it and the class lazy-resolves via `getUserId()` on first method call. **Bootstrap shape: lazy via the class, no `bootstrapDb()` ceremony.** The story sketch offered two integration shapes — explicit `bootstrapDb()` in the layout, or accessors that throw if called pre-bootstrap; the chosen shape (lazy self-bootstrap inside the `Database` class) is cheaper because it leaves all 4 I.w call sites unchanged: `progressRepo.<method>()` calls already await, and the userId resolution rides along on the existing async path. Trade-off: the first method call pays the bootstrap cost (localStorage read + legacy migration check), which is the same cost the old singleton paid on first `getDb()`.
- **`docs/specs/project-essentials.md`** Architecture Quirks section updated with the per-user partitioning, bootstrap shape, auth-migration plan, and the still-open cross-tab anti-clobber caveat.

## [0.57.0] - 2026-05-02

### Changed

- **`getDb` / `persistDb` and `progress.ts` function-style exports replaced with `Database` and `ProgressRepo` classes** (Story I.w). Module-scoped mutable singletons (`let _db`, `let _SQL`, the I.v init-promise pair) are now private instance state on a `Database` class. `progress.ts` becomes a `ProgressRepo` class that takes a `Database` in its constructor. The shape change is what makes the I.v category of bug — module-scoped mutation accessed implicitly by anything that imports the module — structurally impossible: tests construct fresh class instances per case rather than sharing module-level state, and any future async-init footgun becomes a method on a class with a clear owner. [database.ts](src/learningfoundry/sveltekit_template/src/lib/db/database.ts) exports `class Database { #db, #SQL, #dbInitPromise, #sqlInitPromise; getDb(), persist() }`. [progress.ts](src/learningfoundry/sveltekit_template/src/lib/db/progress.ts) exports `class ProgressRepo { constructor(database: Database); markLessonOpened(...), ... }`. [db/index.ts](src/learningfoundry/sveltekit_template/src/lib/db/index.ts) instantiates one of each and exports them as `database` / `progressRepo` singletons. The 3 external callers — [stores/progress.ts](src/learningfoundry/sveltekit_template/src/lib/stores/progress.ts), [LessonView.svelte](src/learningfoundry/sveltekit_template/src/lib/components/LessonView.svelte), [ResetCourseButton.svelte](src/learningfoundry/sveltekit_template/src/lib/components/ResetCourseButton.svelte) — migrated atomically to `progressRepo.<method>(...)` with no deprecated re-exports kept around. SQL strings are unchanged (the upgrade-only conflict CASE clause from Story I.p stays pinned by `progress.test.ts`). Behaviourally identical to v0.56.0 — same DB, same persistence, same singleton-per-page-load semantics; the win is testability and dependency clarity.

### Added

- **`database.test.ts` independent-instances case** (Story I.w). New test asserts that two `new Database()` instances are distinct `===` references and each holds its own internal sql.js Database. The I.v concurrency cases stay, scoped to a single instance. The independent-instances invariant is what Story I.x will build on when `userId` partitioning lands.

## [0.56.0] - 2026-05-02

### Fixed

- **Intermittent progress data loss from `getDb()` init race** (Story I.v). On first page load, multiple call sites hit [database.ts](src/learningfoundry/sveltekit_template/src/lib/db/database.ts) `getDb()` in parallel — curriculum hydrate, the layout `$effect` invalidating progress, and `LessonView` calling `markLessonOpened` — and all callers passed the `if (_db) return _db` gate before any of them finished `await initSqlJs()` / `await loadFromIdb()`. Each constructed its own sql.js `Database` instance; only the *last* assignment to `_db` survived, and `persistDb()` only ever exported that one. Writes through references that won the early race but lost the assignment race were silently dropped — events appeared to write but state reads came back empty, on roughly 50% of deployments depending on microtask scheduling. `initSqlJs()` had the same shape and the same bug invisibly: `_SQL` was checked but never assigned inside the function, so concurrent callers each re-invoked the sql.js factory. Fix: memoise the init promise in both functions via module-scoped `_dbInitPromise` and `_sqlInitPromise` so concurrent callers share the single in-flight initialisation; assign `_db` / `_SQL` inside the IIFE so the synchronous fast path stays warm post-init.

### Added

- **Real-DOM concurrency tests for `getDb()`** (Story I.v). New [database.test.ts](src/learningfoundry/sveltekit_template/src/lib/db/database.test.ts) exercises the actual sql.js + IDB code path with `fake-indexeddb` providing IDB and a `globalThis.fetch` stub serving `static/sql-wasm.wasm` from disk. Two cases: 5 concurrent `getDb()` calls return references that are `===` (single-instance invariant), and a write through one reference is visible via every reference (the user-reported symptom — this is the test that would have caught the bug). Both fail clearly against the pre-fix code and pass after the memoisation.
- `fake-indexeddb` (^6.2.5) as a dev dependency. Standard tool for IDB in vitest+jsdom; no other dep gives a working IndexedDB in the test environment, and stubbing `indexedDB` by hand for sql.js's transaction patterns is brittle.

### Changed

- `vite.config.ts` `test.deps.optimizer.web.exclude = ['sql.js']` added. Without this, vite's pre-bundler eagerly evaluates sql.js's browser build at test startup, which fires the WASM fetch as a module-level side effect and produces an unhandled rejection in jsdom (no fetch base URL for `/sql-wasm.wasm`). Excluding defers sql.js evaluation until a test actually imports it, where the `fetch` stub in `database.test.ts` is already installed.

## [0.55.0] - 2026-05-01

### Added

- **Real-DOM sidebar / dashboard / button test coverage** (Story I.u). Companion to v0.54.0 / I.t — closes the long tail of "the test passes but the rendered DOM doesn't match what the user sees" gaps on the navigation chrome that the existing helper-style tests can't reach. New [ModuleList.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/ModuleList.test.ts) mounts the sidebar with a locked + unlocked module pair: asserts the locked row carries a `<svg class="lucide-lock">` icon and `aria-disabled="true"`, that clicking the locked header does not reveal a `<LessonList>`, that clicking the unlocked header does, and that an active module gets the `border-l-blue-500 bg-blue-50` highlight while inactive siblings do not. New [LessonList.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/LessonList.test.ts) mounts five rows with mixed statuses and pins the rendered glyph for each (`○` / `…` / `✓` / `◇` / `…` for `not_started` / `in_progress` / `complete` / `optional` / `opened`), verifies `aria-disabled="true"` + `cursor-not-allowed` on locked rows with no `goto` on click, and confirms unlocked clicks call `goto('/${moduleId}/${lessonId}')`. [navigation.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/navigation.test.ts) extended with three mount cases: `disabled=true` flips both the native `disabled` attribute and `opacity-50 cursor-not-allowed` classes; in-curriculum click runs `goto(path)` without touching `currentPosition.set`; Finish click (FR-P14 ordering) runs `currentPosition.set(null)` *before* `goto('/')` (verified via `mock.invocationCallOrder`). [ProgressDashboard.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/ProgressDashboard.test.ts) extended with four mount cases: each module card's `<ProgressBar>` width matches the expected percent (parsed from inline `style.width`), the `{#if totalLessons > 0}` gate suppresses the curriculum summary bar when there are zero lessons, a complete module renders "✓ Complete" with no action button while incomplete siblings render "Start module →" / "Continue →". [ResetCourseButton.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/ResetCourseButton.test.ts) rewritten from inline-handler-copy to mount-based — the inline copy stays as a documentation comment so the contract is readable without opening the .svelte file: disabled `<button>` blocks the synthetic click before `confirmFn` is even prompted; cancelled confirm runs no DB or navigation calls; accepted confirm runs `resetProgress` → `currentPosition.set(null)` → `invalidateProgress` → `goto('/')` in that order (FR-P14).

### Changed

- **`vite.config.ts` `testTimeout` bumped from the implicit 5 s default to 15 s.** Component-mount tests pay a one-time vite-transform cost (~4 s) the very first time a file dynamic-imports a Svelte component whose graph pulls in lucide-svelte + marked + katex (`LessonView`, `Navigation`, `ResetCourseButton`). Under serial runs the previous 5 s default left a thin margin; under parallel test-file load the same import landed at 5.1–5.2 s and tipped a green run into a flake. The 15 s ceiling absorbs the cold-compile cost without masking real timeouts (every test in this codebase that *isn't* paying first-import cost completes in <100 ms).

## [0.54.0] - 2026-05-01

### Added

- **Real-DOM lesson-render-pipeline test coverage** (Story I.t). Backfills the component-mount cases the prior FR-P9..FR-P15 stories deferred while Svelte 5 + vitest mounting was unsupported (resolved in v0.52.0 / Story I.q). [TextBlock.observer.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/TextBlock.observer.test.ts) gains two cases that capture the `IntersectionObserver` callback and drive `isIntersecting` directly — one verifies the 1 s in-viewport `ontextcomplete` fire (with re-entry latch), the other locks the early-leave cancel path. [VideoBlock.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/VideoBlock.test.ts) rewritten from helper-only to mount-based: asserts the `<script src=".../iframe_api">` tag injection plus `[id^="yt-player-"]` placeholder render on cold start, exercises the URL-change cycle (prior `YT.Player.destroy()` runs, new player created with the new `videoId`, `fired` latch reset so a second `ENDED` event fires `onvideocomplete` again), and confirms the viewport-fallback `IntersectionObserver` arms after 5 s when `window.YT` never loads. [LessonView.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/LessonView.test.ts) gains the FR-P15 transition matrix at the unit layer: engage transition (first `blockcomplete` → `markLessonInProgress` + `onlessonengage`), complete transition (every block completed → `markLessonComplete` + `invalidateProgress` + `onlessoncomplete`, with `engaged` latch holding `onlessonengage` to one fire), revisit suppression (`getLessonProgress` returns `complete` → `onlessonopen` only — no engage / complete events even when block observers fire), and the zero-block edge case (`onlessonopen` → `markLessonComplete` → `onlessoncomplete` in order with no engage in between).

### Changed

- `LessonView.test.ts` curriculum-store mock replaced wholesale rather than spread-over: the prior `await importOriginal()` pattern still executed `loadCurriculum()` against the unreachable `/curriculum.json` because the actual derived stores closed over the real `curriculum` readable. The new mock returns hand-stubbed readables for every export the component graph touches, so test runs no longer log a noisy `[learningfoundry] Failed to load curriculum: TypeError: Failed to parse URL from /curriculum.json` and the suite is no longer at risk of timing out under the 5 s default when the fetch retry happens to coincide with module compile time.

## [0.53.0] - 2026-05-01

### Fixed

- **Dashboard "Start module →" wrongly displayed for modules with active-but-incomplete lessons.** `ProgressDashboard.svelte`'s `moduleStats()` derived per-module status from `done > 0` (count of `complete` lessons), so a module with an `opened` or `in_progress` lesson — but zero completed lessons — fell back to "Start module →" even though the sidebar correctly showed the lesson as `…`. Regression introduced in v0.45.0 (Story I.j) when the in-progress branch was narrowed from the rollup `mp.status` to a count check, made visible on every lesson click by v0.51.0 (Story I.p, `opened` status). Fix: restore the rollup-based check (`mp.status === 'in_progress'`); optional-lessons handling via `isModuleComplete` is unchanged. Logic extracted into a new `moduleStatus(mod, progress, curriculum?)` helper in `progress-dashboard.helpers.ts` with four anti-regression unit cases (`opened`, `in_progress`, `not_started`, `complete`).

### Removed

- **Workspace-root `sveltekit_template/` duplicate.** The template was duplicated into `src/learningfoundry/sveltekit_template/` in v0.25.0 (PyPI wheel-shipping prep) and `_TEMPLATE_DIR` was repointed at the package copy, but the original at the repo root was never deleted. Nothing read it — verified across Python source, GitHub workflows, `.vscode/settings.json`, `pyproject.toml`, and `.gitignore` (the `*/sveltekit_template/*` and `**/sveltekit_template/static/sql-wasm.wasm` globs match the package copy after deletion). The two copies had already drifted on `curriculum.ts`, `+layout.svelte`, `app.css`, `markdown.ts`, and several test files. Deleting it eliminates the drift hazard and removes a confusing "mirror" step from every story.

### Changed

- `src/learningfoundry/sveltekit_template/` is now the documented single source of truth. `docs/specs/project-essentials.md` "Architecture Quirks" entry updated; `docs/specs/stories.md` gains a top-of-document convention note instructing future stories not to add `sveltekit_template/` "mirror" tasks; one stale relative-path link in `docs/specs/phase-I-progress-ux-subplan.md` repointed at the package copy.

## [0.52.0] - 2026-05-01

### Added

- **Svelte 5 component mount support in vitest** (Story I.q). Component tests can now `render(...)` from `@testing-library/svelte` directly, replacing the source-text and helper-only workarounds used in v0.50.0 and v0.51.0. New [mount.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/mount.test.ts) smoke fails loudly if the config silently reverts. [TextBlock.observer.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/TextBlock.observer.test.ts) rewritten to mount the real component, stub `IntersectionObserver`, capture the observed element, and assert it is the sentinel with non-zero inline height. One previously-deferred I.p case re-instated in [LessonView.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/LessonView.test.ts): asserts `markLessonOpened` resolves before `onlessonopen` fires (lifecycle ordering contract).
- `@testing-library/svelte` and `@testing-library/jest-dom` dev dependencies.

### Changed

- `vite.config.ts` adds `resolve: process.env.VITEST ? { conditions: ['browser'] } : undefined`. Vitest pulls Svelte's browser entry so `mount(...)` works in jsdom; production `vite build` is unaffected (the conditions block is gated on the env var). Documented in `project-essentials.md` under a new "Testing" subsection so the guard isn't stripped in a future "simplify".

## [0.51.0] - 2026-05-01

### Added

- **Lesson `opened` status and three lifecycle event hooks** (Story I.p / FR-P15). `LessonStatus` now runs `not_started → opened → in_progress → complete` (plus the orthogonal `optional`). `LessonView` mounts call new `markLessonOpened` DB op (upgrade-only — never demotes a more advanced status), then dispatch `onlessonopen`. `markLessonInProgress` and `onlessonengage` now fire on the *first* block-completion event of the mount session — not on mount itself — so a learner who opens a lesson but engages with no content is distinguishable from one genuinely partway through. `onlessoncomplete` fires after `markLessonComplete` succeeds. Revisits to a `complete` lesson fire `onlessonopen` only (no engage / complete events when no transition occurs); zero-block lessons fire `onlessonopen` then `onlessoncomplete` in order. No internal subscribers exist today — the events are forward-compatible hooks for future analytics / telemetry adapters.

### Changed

- `markLessonInProgress` is now invoked on the first block-engagement event rather than on mount. SQL itself is unchanged.
- Sidebar icon mapping broadened: `opened` shows the same `…` icon (and `text-blue-500` class) as `in_progress`. The lifecycle distinction is data-only — learners see the same "started" symbol regardless of engagement, by design (FR-P15 / Q2).
- `getModuleProgress`'s module-status derivation: `opened` falls into the `s !== 'not_started'` branch and surfaces as `in_progress` at the module level (intentional; one-line comment added).

## [0.50.0] - 2026-05-01

### Fixed

- **Text-block completion regression introduced in v0.48.0.** The end-of-block sentinel was rendered with `height: 0`, causing `IntersectionObserver` to compute `intersectionRatio = 0` against the configured `0.1` threshold and the `isIntersecting` branch to never fire in real browsers. Net effect: lessons were never marked complete (no sidebar `✓`, no module % movement, no curriculum-bar movement), and revisits couldn't pre-fill the Next/Finish enabled state. The sentinel now renders as `<div data-textblock-end style="height: 1px">` — invisible to learners but observable by the browser. The vitest helper-only suite was unchanged by the regression because it never instantiated a real observer; the e2e harness was unchanged because the spec asserted only sentinel presence rather than actual completion.

### Added

- **TextBlock sentinel anti-regression vitest coverage** ([TextBlock.observer.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/TextBlock.observer.test.ts)): three source-template assertions covering the v0.48.0 zero-area trap — sentinel exists with `data-textblock-end`, carries inline `style="height: 1px"`, and is the element passed to `observer.observe()`. Source-text assertions are brittle to formatting but reliable; mounting Svelte 5 components in vitest (via `@testing-library/svelte` or `svelte/server`) collided with the SvelteKit vite plugin's client-mode compilation, so the canonical cross-check that the markup actually behaves is the e2e harness.
- **Lesson-completion e2e tests** ([progress.spec.ts](src/learningfoundry/sveltekit_template/e2e/progress.spec.ts)): three new cases exercising the FR-P11 user-visible outcome — short-text-block lesson transitions to `✓` in the sidebar without reload; dashboard "X of N completed" increments after completion; revisiting a complete lesson pre-fills Next/Finish as enabled.
- **Tall-text-block scroll-to-complete e2e tests** ([text-block-bottom.spec.ts](src/learningfoundry/sveltekit_template/e2e/text-block-bottom.spec.ts)): rewritten from the prior "structural existence" check. Tall lesson does NOT complete without scroll; scrolling `<main>` to the bottom triggers `✓` within 2 s.
- **Dedicated e2e curriculum fixture** ([e2e/fixtures/curriculum.json](src/learningfoundry/sveltekit_template/e2e/fixtures/curriculum.json) + [e2e/README.md](src/learningfoundry/sveltekit_template/e2e/README.md)): self-contained 3-lesson fixture covering short-text completion and tall-text scroll-to-complete. Specs install a `page.route('**/curriculum.json', …)` interception in `beforeEach` so the harness is decoupled from the smoke build's curriculum drift.

## [0.49.0] - 2026-05-01

### Changed

- **Finish on the last lesson now clears the active-lesson highlight and collapses the previously expanded sidebar module.** When `Navigation.goNext()` finds no next lesson it now sets `currentPosition` to `null` *before* `goto('/')` so the sidebar's auto-expand effect sees the null transition; `computeAutoExpand` was extended to emit a reset (`{expandedModuleId: null, lastAutoExpandedModuleId: null}`) when position clears after a prior auto-expand. Result: landing on the dashboard after Finish shows no module expanded and no lesson row carrying the active highlight, instead of leaving the previously focused lesson visually marked as the learner's current location. The I.f manual-toggle preservation behavior is unchanged (the reset only fires on the position-cleared transition).

## [0.48.0] - 2026-05-01

### Changed

- **TextBlock completion now requires the bottom of the block to be in view, not just any portion.** `TextBlock.svelte` renders a zero-size `<div data-textblock-end aria-hidden="true">` sentinel at the end of the rendered markdown and observes that element rather than the wrapper. A tall lesson can no longer be marked complete simply because the top of the text was on screen on initial render — the learner must scroll until the sentinel is in the viewport for the full 1-second debounce window. The `IntersectionObserver` debounce, threshold (`0.1`), and single-fire `fired` guard are unchanged. New vitest cases cover the "tall block, sentinel never intersects" and "scrolled into view → fires 1 s later" branches.

## [0.47.0] - 2026-05-01

### Added

- **Reset course button.** New `ResetCourseButton.svelte` pinned at the bottom of the sidebar (`mt-auto`). Disabled until any progress exists in the curriculum (any `lesson_progress` row whose status is not `not_started`); reactive activation via the existing `progressStore`. Clicking opens a `window.confirm` dialog; on accept it calls the new `resetProgress()` DB op (single-transaction `DELETE FROM lesson_progress; quiz_scores; exercise_status`), clears `currentPosition`, refreshes the progress store, and routes to `/`. Pure helpers `hasAnyProgress` (in `$lib/utils/progress.ts`) and the new `resetProgress` DB op are independently unit-tested.

## [0.46.0] - 2026-05-01

### Fixed

- **Lesson navigation routing.** Sidebar lesson clicks, the Next/Finish button, and dashboard "Start module / Continue" buttons now call `goto()` from `$app/navigation` directly instead of going through the curriculum store helper. The previous flow updated `currentPosition` (and therefore the sidebar highlight) but left the URL untouched, so the lesson route was never re-mounted: `markLessonInProgress` ran only on the first lesson reached by direct URL, the sidebar checkmarks never updated, and the curriculum/module progress bars stayed at zero across the session. Components now route via `Navigation.svelte`, `LessonList.svelte`, `ProgressDashboard.svelte` → `goto('/${moduleId}/${lessonId}')`.
- **Sticky LessonView state across navigations.** The dynamic lesson route now wraps `<LessonView>` in `{#key \`${moduleId}/${lessonId}\`}` so the subtree tears down and re-mounts whenever either route param changes — guaranteeing fresh `allBlocksComplete` / `completedBlocks` state and a re-run of the on-mount progress check (so revisiting a previously-completed lesson activates Next/Finish immediately).
- **Stale video iframe across consecutive video lessons.** `LessonView`'s `{#each lesson.content_blocks}` now uses a stable identity key derived from `block.ref` or `block.content.url` (falling back to `${type}-${index}`); previously, two consecutive lessons each with a `video` block reused the same `<VideoBlock>` instance and its iframe player, leaving the previous lesson's video on screen. `VideoBlock.svelte` additionally tracks `content.url` via `$effect` and tears down / recreates its YouTube player whenever the URL changes, as belt-and-suspenders coverage.

### Added

- **Playwright e2e harness.** New `e2e/` directory with three regression specs (`navigation.spec.ts`, `progress.spec.ts`, `video.spec.ts`) covering the FR-P9/FR-P10 lifecycle invariants that vitest cannot exercise (because vitest mocks `$app/navigation`). New `pnpm e2e` script and `playwright.config.ts` driving `pnpm preview` against the built static site. The smoke test runs `pnpm e2e` after `pnpm build` and skips gracefully if Playwright browsers aren't installed locally; CI installs them via `pnpm exec playwright install chromium`.
- **Vitest navigation regression coverage.** New `navigation.helpers.ts` (`resolveGoNext`, `resolveGoPrev`, `lessonHref`) and `navigation.test.ts` lock down the routing decisions made by Next/Finish, Previous, and lesson rows. New `contentBlockKey` helper (and tests) verifies the FR-P10 stable-identity convention used by `{#each}`.

### Changed

- `navigateTo` in `$lib/stores/curriculum.ts` is now documented as **internal route-sync only — UI code must use `goto` directly**. The function continues to set `currentPosition` for use by the dynamic lesson route's URL→store `$effect`; UI code (sidebar, dashboard, Next/Finish) routes via `goto()` so SvelteKit's full navigation lifecycle (page params, scroll restoration, `{#key}` re-mount) fires predictably.

## [0.45.0] - 2026-04-30

### Added

- **Locking and unlocking UI.** Frontend implementation of the locking model introduced in v0.44.0:
  - New `$lib/utils/locking.ts` with pure functions `isModuleLocked`, `isLessonLocked`, `getOptionalLessons`, `isModuleComplete`, plus convenience set helpers `lockedModuleIds` / `lockedLessonIds`.
  - `ModuleList.svelte` renders a Lucide `Lock` icon, suppresses expansion, and skips the active-module highlight for locked modules.
  - `LessonList.svelte` shows a `◇` indicator for optional lessons (sibling lessons within a module whose `unlock_module_on_complete` lesson has been completed) and renders locked lessons as muted, non-clickable rows.
  - `ProgressDashboard.svelte` uses `isModuleComplete` for per-module status (treats optional lessons as not blocking module completion) while still counting all completed lessons toward the curriculum-level progress bar.
  - Type extensions: `LessonStatus` gains `'optional'`; `Lesson.unlock_module_on_complete?`, `Module.locked?`, `Curriculum.locking?`, and a new `LockingConfig` interface.
  - The unlock cascade is fully reactive: completing an `unlock_module_on_complete` lesson refreshes `progressStore` once via `invalidateProgress`, and all locked/optional state re-derives automatically — no extra DB writes or store updates required.

## [0.44.0] - 2026-04-30

### Added

- **Locking configuration schema.** Python-side schema, resolver, and config support for sequential content access control:
  - `LockingConfig` Pydantic model (`sequential`, `lesson_sequential`) on `CurriculumDef`.
  - `Module.locked: bool | None` per-module override.
  - `Lesson.unlock_module_on_complete: bool` gateway-lesson flag.
  - `QuizBlock.pass_threshold: float` (0.0–1.0) for quiz completion scoring.
  - Global config (`~/.config/learningfoundry/config.yml`) gains `locking` block with the same fields.
  - Config hierarchy: global defaults → curriculum YAML `locking` → per-module `locked` override.
  - All fields propagate through the resolver into `curriculum.json` for frontend consumption (Story I.j).

## [0.43.0] - 2026-04-30

### Added

- **Curriculum-level progress bar on the dashboard.** `ProgressDashboard.svelte` now renders a summary bar above the module cards showing `"{totalComplete} of {totalLessons} lessons completed"`. Computed reactively from `progressStore` — updates live when lessons complete during the session. Hidden when the curriculum has zero lessons. The dashboard `+page.svelte` no longer does its own one-shot progress fetch; it reads from the shared `progressStore` populated by the layout.

## [0.42.0] - 2026-04-30

### Added

- **Block completion events drive lesson auto-complete.** Each content block fires an independent completion event when sufficiently engaged with: `TextBlock` after 1 s in the viewport (IntersectionObserver + debounce timer), `VideoBlock` on YouTube IFrame Player API `ENDED` state (falls back to 3 s viewport if API fails to load within 5 s), `QuizBlock` when score ≥ `passThreshold` (default 0.0). `LessonView` tracks which blocks have completed; when all have fired, the lesson is marked complete in SQLite and the sidebar updates immediately.
- **Reactive progress store** (`$lib/stores/progress.ts`). `progressStore` is a writable Svelte store holding `Record<string, ModuleProgress>`. `invalidateProgress(curriculum)` re-fetches all module progress from SQLite and writes to the store. `+layout.svelte` subscribes to this store instead of a one-shot `$effect` fetch; lesson completions call `invalidateProgress` so the sidebar reflects changes without a page reload.
- **Revisit behaviour.** On mount, `LessonView` reads the lesson's current DB status; if already `complete`, all blocks are pre-filled as done so the Next/Finish button is immediately active.
- **Zero-block edge case.** A lesson with no content blocks is treated as immediately complete on mount.
- **`QuizManifest.passThreshold`** added to TypeScript types for future quiz scoring threshold support.

### Changed

- **Next/Finish no longer trigger completion marking.** Navigation is decoupled from completion: `Navigation.svelte` handles its own routing (Next → `navigateTo`, Finish → `goto('/')`) and accepts a `disabled` prop. The `onComplete` callback prop has been removed. `LessonView` no longer has `handleNavComplete` or `oncomplete`.
- **`+page.svelte`** migrated from deprecated `$app/stores` to `$app/state` for route params.

## [0.41.0] - 2026-04-30

### Fixed

- **Finish button on last lesson now navigates to the dashboard.** `+page.svelte` was not passing an `oncomplete` handler to `<LessonView>`; clicking Finish was a no-op. It now calls `goto('/')` to redirect to the progress dashboard.
- **Sidebar module expand/contract no longer reverts immediately.** The `$effect` in `ModuleList.svelte` read `expandedModuleId` (the value it writes), creating a self-dependency that overwrote manual toggles on every re-run. A separate `lastAutoExpandedModuleId` state variable breaks the cycle — the effect only fires when `currentPosition.moduleId` changes to a genuinely new value.
- **Active module in sidebar is now visually highlighted.** The module card containing the current lesson receives a left-border accent (`border-l-2 border-l-blue-500`) and a light background tint (`bg-blue-50`).

## [0.40.0] - 2026-04-29

### Added

- **Video blocks declare a `provider` and optional `extensions`.** `provider` defaults to `youtube` so existing curricula are unchanged. `extensions` is an arbitrary JSON object carried verbatim through resolve → `curriculum.json` for player-specific features (chapters, transcripts, etc.) without a one-size-fits-all schema. Only `youtube` is implemented today; the Svelte `VideoBlock` dispatches on `provider` and treats missing `provider` in older JSON as `youtube`.
  - `src/learningfoundry/schema_v1.py` — `VideoBlock` gains `provider: Literal["youtube"]` and `extensions: dict[str, Any]`; URL validation runs in a `@model_validator` per provider. `YOUTUBE_URL_RE` is the single regex shared with the resolver.
  - `src/learningfoundry/resolver.py` — video `content` now includes `url`, `provider`, and `extensions`.
  - `src/learningfoundry/sveltekit_template/src/lib/types/index.ts` — `VideoProvider` type and `VideoContent` optional fields.
  - `src/learningfoundry/sveltekit_template/src/lib/components/VideoBlock.svelte` — provider branch for YouTube embed; placeholder branch for future providers. Workspace-root `sveltekit_template/` kept in sync.

### Documentation

- `README.md` — new "Video blocks" section and YAML comments for `provider` / `extensions`.
- `docs/specs/features.md`, `docs/specs/tech-spec.md` — video block fields updated.

### Added (tests)

- `tests/test_schema_v1.py` — defaults, explicit `provider`, `extensions` dict.
- `tests/test_resolver.py` — resolved `content` includes `provider` + `extensions`; extensions round-trip.
- `tests/test_smoke_sveltekit.py` — `build/curriculum.json` video block includes `provider` and `extensions`.

## [0.39.0] - 2026-04-29

### Added

- **Module `description` from `curriculum.yml` now appears on the course overview (home) page.** The field was parsed, resolved, and emitted in `curriculum.json` all along — `ProgressDashboard.svelte` simply never rendered it. Each module card now shows a muted one-line paragraph under the title when `description` is non-empty.
  - `src/learningfoundry/sveltekit_template/src/lib/components/ProgressDashboard.svelte` — `{#if mod.description}` block with `text-xs leading-relaxed text-gray-500` between the title row and the progress bar (mirrored in workspace-root `sveltekit_template/` for parity with local copies).

### Added (tests)

- `tests/test_resolver.py::TestResolvedTypes::test_module_description_round_trips` — asserts a non-empty module `description` survives `resolve_curriculum()`.
- `tests/test_smoke_sveltekit.py::TestSvelteKitSmokeBuild::test_curriculum_json_valid_in_build` — asserts `build/curriculum.json` carries the fixture's first-module description (`"First module."`) and the second module has an empty or omitted description.

## [0.38.0] - 2026-04-29

### Fixed

- **Clicking "Next" at the end of a lesson no longer drops the user at the bottom of the new lesson.** The shell layout pins the viewport (`h-screen overflow-hidden`) and scrolls inside `<main>`, but SvelteKit's built-in scroll restoration only manages `window.scrollY`. As a result, navigating from the bottom of one lesson (where the Next button lives) left `<main>.scrollTop` at the previous bottom; the new page rendered correctly but landed at the footer. The same bug affected sidebar lesson clicks made from anywhere below the fold.
  - `src/learningfoundry/sveltekit_template/src/routes/+layout.svelte` — bound a ref to the `<main>` element and registered an `afterNavigate` hook that resets `mainEl.scrollTop = 0` on every forward navigation. `popstate` (browser back/forward) is left alone so the browser's native scroll restoration still works for those.
  - `src/learningfoundry/sveltekit_template/src/routes/layout.scroll.ts` (new) — extracted the reset logic into a pure helper (`resetMainScrollOnForwardNav`) so it can be unit-tested without mounting the full layout.

### Added (tests)

- `src/learningfoundry/sveltekit_template/src/routes/layout.scroll.test.ts` — 5 vitest cases verifying that `resetMainScrollOnForwardNav` resets `scrollTop` for `link`, `goto`, and `form` navigations, leaves it alone for `popstate`, and is a no-op when the element ref is undefined (the bound ref can be undefined during the first navigation before mount).

## [0.37.0] - 2026-04-29

### Added

- **First-class support for co-located image assets in lesson markdown.** Authors can now reference images directly from a lesson's markdown using either the markdown form (`![alt](path)`, `![alt](path "title")`) or the HTML form (`<img src="path">`); relative paths are resolved against the markdown file's own directory so authors keep images next to the markdown that uses them. `learningfoundry build` copies each unique image into `dist/static/content/<sha256[:12]>/<basename>` and rewrites the markdown URL to the absolute path `/content/<sha256[:12]>/<basename>` so it resolves at every nested route in the generated app. Same image referenced from N lessons → copied once (deduped by content hash). Absolute URLs (`https://`, `http://`, `//`, leading `/`, `data:` URIs) pass through unchanged so authors can mix CDN-hosted and co-located images. Image refs inside fenced code blocks (`` ``` `` or `~~~`) are left as literal text so code samples that demonstrate image syntax aren't silently rewritten. Missing images fail the build with the lesson location AND the expected on-disk path in the error message.
  - New module `src/learningfoundry/asset_resolver.py` — pure function `resolve_markdown_assets(markdown, markdown_path) → (rewritten_markdown, list[Asset])`. Skips fenced code blocks, normalises query/fragment off the on-disk lookup, and dedupes by `dest_relative` (= content hash).
  - `src/learningfoundry/resolver.py` — text-block resolution now invokes `resolve_markdown_assets()`; `ResolvedCurriculum` gained a top-level `assets: list[Asset]` field aggregated globally across modules/lessons (deduped by content hash).
  - `src/learningfoundry/generator.py` — new `_copy_assets()` step copies each `Asset` into `output_dir/static/<dest_relative>` (idempotent on matching size, since the path is content-hashed). `_write_curriculum_json()` now strips `assets` from the serialised tree (the field carries on-disk `Path` objects and is consumed only by the generator).
  - `_PRESERVED_PATHS` extended with `"static/content"` so previously-copied image assets survive a `learningfoundry build` re-run alongside `node_modules/`, `pnpm-lock.yaml`, `build/`, and `.svelte-kit/`.

### Documentation

- `README.md` — new "Images and assets" section in the Table of Contents with a worked example, the rules for relative vs. absolute URLs, the dedup-by-hash behaviour, and a note on how `static/content/` flows through to `build/content/` for static-export deployment.
- `docs/specs/features.md` — Inputs section documents the image co-location convention; Outputs section documents the generated `static/content/<hash12>/<basename>` directory; FR-2 (Content Resolution) gained an "Image asset resolution" sub-requirement covering the regex strategy, passthrough rules, dedup, and error semantics.
- `docs/specs/tech-spec.md` — added `asset_resolver.py` to Package Structure; added a new "asset_resolver.py — Markdown Image Asset Resolution" Key Component Design section; updated the `resolver.py` and `generator.py` sections to describe the asset hand-off; documented `Asset` and the `assets` field in Data Models.

### Added (tests)

- `tests/test_asset_resolver.py` — 19 cases covering relative-image resolution, subdirectory paths, title attributes, all five passthrough URL forms, missing-file error messages, dedup of identical content, hash separation of same-basename-different-bytes, HTML `<img>` (single + double quoted), fenced-code-block skipping for both `` ``` `` and `~~~`, query/fragment stripping, no-image no-op, and the `Asset.url_path` property.
- `tests/test_resolver.py::TestTextBlockImageAssets` — 4 cases asserting that `resolve_curriculum()` populates `ResolvedCurriculum.assets`, rewrites lesson markdown to `/content/...` URLs, surfaces missing-image errors with the lesson location, and dedupes assets across lessons.
- `tests/test_generator.py::TestImageAssetCopy` (4 cases) and `TestStaticContentPreserved` (2 cases) — verify that `Asset` records land on disk under `static/<dest_relative>`, that `assets` is stripped from `curriculum.json`, that absent assets don't create an empty `static/content/`, that rebuilds are idempotent on unchanged assets, and that an existing `static/content/` survives a rebuild.
- `tests/test_smoke_sveltekit.py::test_co_located_image_reaches_build_output` — added a co-located `diagram.png` to `tests/fixtures/content/mod-01/` (referenced from `lesson-01.md`) and asserts the image lands at `build/content/<hash12>/diagram.png` after the full `learningfoundry build → pnpm install → pnpm build` smoke pipeline.

## [0.36.0] - 2026-04-29

### Changed

- **`learningfoundry preview` is now the canonical "see your work" command.** Previously the post-build prompt and the README disagreed: the CLI told users to `cd dist && pnpm install && pnpm build` (a static export that exits without serving), while the README told them to run `learningfoundry preview`. Users following whichever doc they read first ended up with redundant work or wasted `pnpm install` invocations. The CLI's post-build prompt now consistently points at `learningfoundry preview` for every `DepState`, with `cd dist && pnpm build` mentioned only as the "for a static export to deploy" alternative.
  - `src/learningfoundry/cli.py` — collapsed the three-branch `DepState` prompt into a single message: `Next: learningfoundry preview` (with a `⚠️  Dependencies changed …` line prepended in the `CHANGED` case so the user knows the upcoming `learningfoundry preview` will reinstall).
  - `README.md` — Quick Start step 3 now combines build+preview into one `learningfoundry preview` invocation; the `learningfoundry preview` reference section explicitly notes that it serves the SvelteKit project from source via Vite (not the `pnpm build` static output) and now skips `pnpm install` when nothing has changed.

### Performance

- **`learningfoundry preview` no longer runs `pnpm install` on every invocation.** It now consults `check_dep_state(output_dir)` and skips the install step entirely when the state is `UNCHANGED` (every declared dep is already present in `node_modules/`). Subsequent `learningfoundry preview` runs after a content edit go straight to `pnpm run dev`, saving 5–30 s per cycle. The install still runs unconditionally on `FIRST_BUILD` and `CHANGED` states.
  - `src/learningfoundry/pipeline.py::run_preview` — imports `DepState` and `check_dep_state`; logs `Dependencies up to date — skipping pnpm install.` when the state is `UNCHANGED`.

### Added (tests)

- `tests/test_cli.py::TestBuildNextStepsPrompt` — 3 cases asserting the new build prompt wording for `FIRST_BUILD`, `UNCHANGED`, and `CHANGED` states (each must say `Next: learningfoundry preview`; only `CHANGED` mentions the dep-change warning).
- `tests/test_pipeline.py::TestRunPreviewSkipsInstall` — 3 cases verifying that `run_preview` invokes `pnpm install` on `FIRST_BUILD` and `CHANGED` but not on `UNCHANGED`, while always invoking `pnpm run dev`.

## [0.35.0] - 2026-04-29

### Fixed

- **Block math (`$$ … $$`) now renders reliably even when the delimiter lines have stray whitespace.** `marked-katex-extension`'s upstream block regex requires the opening `$$` to be followed immediately by `\n` and the closing `$$` to be followed immediately by `\n` or end-of-string — any leading or trailing whitespace on a delimiter-only line silently breaks the match, falling through to default paragraph rendering and emitting literal `$$ … $$` text in the page. Real-world markdown frequently has trailing spaces on these lines (editor quirks, copy-paste from PDFs/chat/docs), so this was easy to trip into.
  - `src/learningfoundry/sveltekit_template/src/lib/utils/markdown.ts` — `renderMarkdown()` now normalises any line that is *only* whitespace + `$$` + whitespace down to bare `$$` before handing the source to `marked.parse()`. Inline math (`$x$`) and the markdown "trailing two spaces = `<br>`" rule on regular text are unaffected because the regex requires the line to consist of nothing but the delimiter.

### Added (tests)

- `src/learningfoundry/sveltekit_template/src/lib/utils/markdown.test.ts` — 3 new vitest cases covering trailing-whitespace-after-closing-`$$`, leading-whitespace-before-closing-`$$`, and trailing-whitespace-after-opening-`$$`. Each now produces `class="katex"` and `katex-display` in the rendered HTML.

## [0.34.0] - 2026-04-29

### Changed

- **`learningfoundry build` now preserves install/build state across rebuilds.** Previously every rebuild wiped the entire output directory, including any existing `node_modules/`, `pnpm-lock.yaml`, `build/`, and `.svelte-kit/` — forcing the user to `pnpm install` after every regen. Now those four paths are moved into the fresh template copy before the swap, so iteration is install → build, then any number of `learningfoundry build` re-runs followed by just `pnpm build` (or `pnpm dev`).
  - `src/learningfoundry/generator.py` — new `_PRESERVED_PATHS` list + `_move_preserved()` helper used by `_atomic_copy()`. Same paths are also passed to `shutil.ignore_patterns` so a stray `node_modules/` in the dev template directory never ships to user output.
  - The "output directory exists" log message changed from `WARNING` ("will be overwritten") to `INFO` ("refreshing template files; preserving …") to reflect the new behaviour.

### Added

- **Smart post-build next-steps message in the CLI** based on detected dep state:
  - `FIRST_BUILD` (no `node_modules/`) → `Next: cd dist && pnpm install && pnpm build`
  - `CHANGED` (any declared dep missing from `node_modules/`) → `⚠️  Dependencies changed since last install. Run: cd dist && pnpm install && pnpm build`
  - `UNCHANGED` (every declared dep present) → `Next: cd dist && pnpm build`
- New public API: `learningfoundry.generator.check_dep_state(output_dir)` returning a `DepState` enum, used by the CLI but also callable from third-party tooling.

### Added (tests)

- `tests/test_generator.py::TestPreserveInstallState` — 5 cases covering preservation of `node_modules/`, `pnpm-lock.yaml`, `build/`, `.svelte-kit/`, and confirmation that template files (e.g. `curriculum.json`) still refresh on rebuild.
- `tests/test_generator.py::TestCheckDepState` — 4 cases covering first-build, all-deps-installed, missing-dep, and malformed-`package.json` paths.

### Performance

- Smoke build is ~40% faster (~10s vs ~17s) because the SvelteKit template's leftover dev `node_modules/` (which a developer's local pnpm runs may create in the in-repo template) is no longer copied into every `learningfoundry build` output.

## [0.33.0] - 2026-04-29

### Added

- **LaTeX math rendering in lesson markdown** via [KaTeX](https://katex.org/). Both inline (`$...$`) and display (`$$...$$`) syntax are supported and rendered to HTML at parse time — no runtime JS overhead per lesson view.
  - `src/learningfoundry/sveltekit_template/package.json` — added `katex ^0.16.11` and `marked-katex-extension ^5.1.4` to dependencies
  - `src/learningfoundry/sveltekit_template/src/lib/utils/markdown.ts` — registered `markedKatex({ throwOnError: false })` so malformed LaTeX renders the source verbatim instead of throwing
  - `src/learningfoundry/sveltekit_template/src/app.css` — `@import 'katex/dist/katex.min.css';` so rendered formulas are styled

### Added (tests)

- `src/learningfoundry/sveltekit_template/src/lib/utils/markdown.test.ts` — 6 vitest cases covering blank input, headings, fenced code, inline math, display math, and graceful malformed-LaTeX handling
- `tests/test_smoke_sveltekit.py::test_katex_styles_in_bundled_css` — regression guard asserting `.katex` rules land in the bundled CSS

## [0.32.0] - 2026-04-29

### Fixed

- **Markdown headings, lists, and code in rendered lesson content had no styling** — they all displayed at body-text size. `TextBlock.svelte` applies the Tailwind `prose prose-slate` classes, but `@tailwindcss/typography` was never installed or registered, so the `prose` class was an unknown utility and the marked-rendered HTML fell through to browser defaults (which Tailwind's preflight reset flattens).
  - `src/learningfoundry/sveltekit_template/package.json` — added `@tailwindcss/typography ^0.5.16` to devDependencies
  - `src/learningfoundry/sveltekit_template/src/app.css` — registered the plugin via Tailwind v4's CSS-first `@plugin '@tailwindcss/typography';` directive

### Added

- `tests/test_smoke_sveltekit.py::test_typography_prose_styles_in_bundled_css` — regression guard asserting `.prose` is present in the compiled bundle CSS, so an accidental removal of the plugin will fail the smoke suite.

## [0.31.0] - 2026-04-27

### Fixed

- **Clicking "Finish" on the final lesson did nothing visible.** `Navigation.goNext()` correctly calls `onComplete?.()` when there is no next lesson; `LessonView.handleNavComplete()` correctly marks the lesson complete and bubbles the event up via its own `oncomplete` prop — but `routes/[module]/[lesson]/+page.svelte` never passed an `oncomplete` handler, so the chain ended silently. The lesson was marked complete in IndexedDB, but the user stayed on the same page with no feedback.
  - `src/learningfoundry/sveltekit_template/src/routes/[module]/[lesson]/+page.svelte` — added `handleLessonComplete()` that calls `goto('/')`, returning the learner to the dashboard where progress badges reflect the completion.

## [0.30.0] - 2026-04-27

### Fixed

- **`Cannot call fetch eagerly during server-side rendering with relative URL (/curriculum.json)`** — SvelteKit's prerender pass was subscribing to the `curriculum` readable store during SSR of `+layout.svelte`, triggering a relative-URL fetch on the server. The template is a pure CSR SPA (runtime curriculum fetch, IndexedDB, sql.js/WASM) and was never intended to render on the server.
  - `src/learningfoundry/sveltekit_template/src/routes/+layout.ts` — new file exporting `ssr = false` and `prerender = false`. With `adapter-static` + `fallback: 'index.html'` already configured in `svelte.config.js`, the SPA fallback handles every route client-side; prerendering is not needed and was failing on dynamic `[module]/[lesson]` routes anyway.

## [0.29.0] - 2026-04-27

### Fixed

- **Lesson content never rendered after clicking "Start module" / Next / Previous.** `navigateTo`, `navigateNext`, and `navigatePrev` in the SvelteKit template only updated the `currentPosition` Svelte store; they never changed the URL. Because lesson content is mounted by the dynamic route `/[module]/[lesson]/+page.svelte`, the route was never visited and `LessonView` (which renders the inlined markdown) never mounted — the left nav title updated, but the content area stayed on the home dashboard.
  - `src/learningfoundry/sveltekit_template/src/lib/stores/curriculum.ts` — `navigateTo` now also calls `goto('/${moduleId}/${lessonId}')`; `navigateNext` and `navigatePrev` refactored to compute the target and delegate to `navigateTo` so URL navigation happens for them too.

### Added

- **Frontend unit-test infrastructure** for the SvelteKit template (the navigation regression went uncaught because the template had no test suite):
  - `sveltekit_template/package.json` — added `jsdom` to devDependencies (`vitest` was already present)
  - `sveltekit_template/vite.config.ts` — added vitest config block (`environment: 'jsdom'`, `include: src/**/*.{test,spec}.{js,ts}`)
  - `sveltekit_template/src/lib/stores/curriculum.test.ts` — 9 cases covering `navigateTo` (URL + store update), `navigateNext` (within module / across modules / final-lesson no-op / null position), `navigatePrev` (within module / across modules / first-lesson no-op / null position); mocks `$app/navigation`'s `goto` via `vi.mock` and stubs global `fetch` to seed the curriculum readable
- `tests/test_smoke_sveltekit.py::test_pnpm_test_passes` — runs `pnpm test` (vitest) inside the installed template so the smoke run catches future frontend regressions

### Verified

- `pyve test -m smoke` — 7/7 passed (Python build + vitest)
- Full Python suite — 195/195 passed; ruff and mypy clean

## [0.28.0] - 2026-04-26

### Fixed

- `pip install "learningfoundry[quizazz]"` now resolves: the `quizazz` extra pointed at the non-existent PyPI package `quizazz-builder`. The actual package (per `docs/specs/quizazz-README.md`) is published as `quizazz`.

### Changed

- `pyproject.toml` — `[project.optional-dependencies] quizazz` now requires `quizazz>=0.1` (was `quizazz-builder>=0.1`); `[[tool.mypy.overrides]] module = "quizazz"` (was `"quizazz_builder"`)
- `src/learningfoundry/integrations/quizazz.py` — imports `from quizazz import compile_assessment` (was `from quizazz_builder`); error messages and docstrings updated
- `tests/test_integrations/test_quizazz.py` — `sys.modules` mocks and `ImportError` match pattern updated to `quizazz`
- `src/learningfoundry/resolver.py` — docstring reference updated
- `README.md` — quiz block link points to `pointmatic/quizazz` (was `quizazz-builder`)

## [0.27.0] - 2026-04-15

### Added

- `requirements-dev.txt` — added `pytest-cov>=7.0`
- `pyproject.toml` — `[tool.coverage.run]` (source, omit sveltekit_template) and `[tool.coverage.report]` (exclude_lines)
- `.github/workflows/ci.yml` — test job now runs `--cov=src/learningfoundry --cov-report=xml`; uploads `coverage.xml` to Codecov via `codecov/codecov-action@v4` (`fail_ci_if_error: false`)
- `README.md` — CI status badge and Codecov coverage badge

### Verified

- Local coverage run: **95%** (458 statements, 25 missed)

## [0.26.0] - 2026-04-15

### Added

- `.github/workflows/ci.yml` — CI workflow triggered on push/PR to `main`:
  - `lint` job: Python 3.12, installs `requirements-dev.txt`, runs `ruff check .` then `mypy src/`
  - `test` job: Python 3.12, installs package + dev deps, runs `pytest` (smoke tests excluded)
  - Jobs run in parallel; standard `actions/setup-python` used (pyve is local-only tooling)

## [0.25.0] - 2026-04-15

### Added

- `pyproject.toml` — `readme`, `keywords`, `classifiers` (Beta, Apache, Python 3.12, Education, Code Generators, Typed), `[project.urls]` (Homepage, Repository, Bug Tracker, Changelog), `[tool.hatch.build.targets.sdist]` include list
- `src/learningfoundry/sveltekit_template/` — template copied into package so it ships in the wheel

### Fixed

- `src/learningfoundry/generator.py` — `_TEMPLATE_DIR` now uses `Path(__file__).parent / "sveltekit_template"` (was `../../../sveltekit_template`); template now resolves correctly in installed environments

### Verified

- `pyve run hatch build` — `dist/learningfoundry-0.25.0-py3-none-any.whl` and `.tar.gz` produced
- Wheel contains 31 `sveltekit_template/` files
- `pip install dist/learningfoundry-0.25.0-py3-none-any.whl` in clean venv — `learningfoundry --version` → `0.25.0`; `_TEMPLATE_DIR.exists()` → `True`
- `pyve test -q` — 195 passed

## [0.24.0] - 2026-04-15

### Added

- `README.md` — full user-facing documentation: overview, installation, quick start, CLI reference (build/validate/preview with all flags and exit codes), curriculum YAML format with all 5 block types, configuration file reference, development setup, project structure

## [0.23.0] - 2026-04-15

### Added

- `tests/test_smoke_sveltekit.py` — 6 end-to-end smoke tests (marked `smoke`, excluded from default `pyve test` run):
  - `test_pnpm_install_succeeds` — `node_modules/` created
  - `test_pnpm_build_produces_build_dir` — `build/` directory exists
  - `test_build_produces_index_html` — `build/index.html` present
  - `test_curriculum_json_present_in_build` — `build/curriculum.json` copied by vite
  - `test_curriculum_json_valid_in_build` — JSON is valid with 2 modules
  - `test_build_contains_js_assets` — at least one `.js` file in build output
- `pyproject.toml` — registered `smoke` marker; smoke file excluded from `addopts` so `pyve test` stays fast
- Smoke tests use `scope="module"` fixtures so `pnpm install` + `pnpm build` run once per session

### Verified

- `pyve test tests/test_smoke_sveltekit.py -v` — 6 passed in ~13 s
- `pyve test -q` — 195 passed (smoke excluded, fast)
- `ruff check .` and `mypy src/` — clean

## [0.22.0] - 2026-04-15

### Added

- `pyproject.toml [tool.mypy]` — `strict = true`, `python_version = "3.12"`, `[[tool.mypy.overrides]]` for `quizazz_builder` (`ignore_missing_imports = true`)
- `pyproject.toml [tool.ruff.lint]` — expanded select to `["E", "F", "I", "UP", "W", "B"]` (adds pycodestyle warnings + flake8-bugbear)
- Installed `mypy` and `types-PyYAML` into testenv

### Fixed

- `src/learningfoundry/integrations/quizazz.py` — removed stale `# type: ignore[import-untyped]`; now covered by mypy overrides
- `scripts/spike_e2e.py` — removed unused `shutil` import

### Verified

- `pyve testenv run ruff check .` — 0 errors (with W + B rules)
- `pyve testenv run mypy src/` — 0 errors (16 source files, strict)
- `pyve test -q` — 195 passed

## [0.21.0] - 2026-04-15

### Added

- `tests/test_edge_cases.py` — 22 new tests across 6 classes:
  - `TestEmptyCurriculum` — schema rejects empty modules/lessons; generator handles zero-module `ResolvedCurriculum`; `run_validate` returns False for empty-module YAML; lesson-with-no-blocks resolves fine
  - `TestAllBlockTypesTogether` — all 5 block types resolved in order; all are `ResolvedContentBlock`; `curriculum.json` contains all 5 types
  - `TestLargeCurriculum` — 5 modules × 4 lessons; all modules/lessons resolved; generated JSON counts correct; spot-check text content
  - `TestIntegrationRunBuild` — full `run_build` with fixture curriculum (all block types) through real generator; `curriculum.json` has 2 modules; mod-01 has all 5 block types; `package.json` present
  - `TestValidateResolutionErrors` — missing text-block file returns False with error; error message includes location context
  - `TestOptionalFields` — missing `description` defaults to `""`; missing assessments resolve to `None`

### Verified

- `pyve test` — 195 passed, 0 failed

## [0.20.0] - 2026-04-15

### Added

- `src/learningfoundry/cli.py` — `preview` subcommand: calls `run_preview()`, accepts `--port` (default 5173), prints `http://localhost:{port}` on success; same error/exit-code handling as `build`
- `tests/test_cli.py` — 6 new preview tests: help, delegation to `run_preview`, URL output, default port, validation error exit, generation error exit (21 total CLI tests)

## [0.19.0] - 2026-04-15

### Added

- `src/learningfoundry/cli.py` — `build` subcommand (parse→resolve→generate, `--config`, `--output`, `--base-dir`, `--log-level`); `validate` subcommand (parse→resolve only, reports OK/errors); exit codes 1=validation, 2=resolution, 3=generation, 4=config
- `tests/test_cli.py` — 15 tests: `--help`/`--version`, build success/error paths, validate OK/invalid/missing/config-error
- `tests/conftest.py` — `reset_learningfoundry_logger` autouse fixture; fixes caplog isolation across all test modules

### Fixed

- Cross-module `caplog` interference caused by `setup_logging()` leaving handlers on the `learningfoundry` logger — now reset after every test via `conftest.py`

## [0.18.0] - 2026-04-15

### Added

- `sveltekit_template/src/lib/components/LessonView.svelte` — renders all content blocks for a lesson, marks lesson in-progress on mount, marks complete on nav-next, propagates quiz scores
- `sveltekit_template/src/routes/+layout.svelte` — app shell: sidebar (`ModuleList`) + main content slot; loads module progress from SQLite reactively
- `sveltekit_template/src/routes/+page.svelte` — landing page with `ProgressDashboard`
- `sveltekit_template/src/routes/[module]/[lesson]/+page.svelte` — lesson route; syncs URL params to curriculum store; renders `LessonView`

### Verified

- `pnpm exec svelte-check` — 0 errors, 0 warnings
- `pnpm build` — full adapter-static build succeeds; all routes compiled

## [0.17.0] - 2026-04-15

### Added

- `sveltekit_template/src/lib/components/ProgressBar.svelte` — accessible progress bar with clamped percent and optional label
- `sveltekit_template/src/lib/components/LessonList.svelte` — lesson list with status icons (✓/…/○) and active highlight
- `sveltekit_template/src/lib/components/ModuleList.svelte` — collapsible module sidebar with per-module `ProgressBar`; auto-expands active module via `$effect`
- `sveltekit_template/src/lib/components/Navigation.svelte` — prev/next lesson buttons using `lucide-svelte` chevrons; "Finish" on last lesson; fires `onComplete`
- `sveltekit_template/src/lib/components/ProgressDashboard.svelte` — overall + per-module progress bars, pre/post assessment scores, start/continue/complete actions

### Verified

- `pnpm exec svelte-check` — 0 errors, 0 warnings

## [0.16.0] - 2026-04-15

### Added

- `sveltekit_template/src/lib/utils/markdown.ts` — `renderMarkdown()` using `marked`
- `sveltekit_template/src/lib/components/PlaceholderBlock.svelte` — generic "coming soon" placeholder
- `sveltekit_template/src/lib/components/TextBlock.svelte` — renders markdown via `{@html}` with `$derived`
- `sveltekit_template/src/lib/components/VideoBlock.svelte` — YouTube embed (converts watch/youtu.be URLs to embed URLs)
- `sveltekit_template/src/lib/components/QuizBlock.svelte` — quizazz manifest placeholder; writes score to SQLite on complete
- `sveltekit_template/src/lib/components/ExerciseBlock.svelte` — renders exercise content or stub placeholder
- `sveltekit_template/src/lib/components/VisualizationBlock.svelte` — renders SVG/image or stub placeholder
- `sveltekit_template/src/lib/components/ContentBlock.svelte` — type dispatcher for all block types
- `sveltekit_template/package.json` — added `marked ^18.0.0`

### Verified

- `pnpm exec svelte-check` — 0 errors, 0 warnings

## [0.15.0] - 2026-04-15

### Added

- `sveltekit_template/src/lib/db/database.ts` — sql.js init with WASM locator, IndexedDB persistence (`getDb()`, `persistDb()`), DDL for `lesson_progress`, `quiz_scores`, `exercise_status`
- `sveltekit_template/src/lib/db/progress.ts` — `markLessonComplete()`, `markLessonInProgress()`, `getLessonProgress()`, `saveQuizScore()`, `getQuizScore()`, `updateExerciseStatus()`, `getModuleProgress()`
- `sveltekit_template/src/lib/db/index.ts` — barrel re-export
- `sveltekit_template/package.json` — `postinstall` script copies `sql-wasm.wasm` to `static/`; added `@types/sql.js ^1.4.11`
- `sveltekit_template/static/.gitkeep` — tracks static dir in git
- `.gitignore` — ignores `sveltekit_template/static/sql-wasm.wasm`

### Verified

- `pnpm exec svelte-check` — 0 errors

## [0.14.0] - 2026-04-15

### Added

- `sveltekit_template/src/lib/types/index.ts` — all TypeScript interfaces: `TextContent`, `VideoContent`, `QuizManifest`, `QuizQuestion`, `QuizAnswer`, `ExerciseContent`, `VisualizationContent`, `ContentBlock`, `Lesson`, `Module`, `Curriculum`, `LessonProgress`, `QuizScore`, `ModuleProgress`, `CurriculumProgress`
- `sveltekit_template/src/lib/stores/curriculum.ts` — `curriculum` readable (loads `curriculum.json`), `currentPosition` writable, derived stores `modules`, `currentModule`, `currentLesson`, `lessonSequence`, `currentIndex`, `previousLesson`, `nextLesson`, and `navigateTo/navigateNext/navigatePrev` helpers

### Verified

- `pnpm exec svelte-kit sync && pnpm exec svelte-check` — 0 errors

## [0.13.0] - 2026-04-15

### Added

- `sveltekit_template/package.json` — full deps: `svelte@^5`, `@sveltejs/kit@^2`, `@sveltejs/adapter-static@^3`, `sql.js`, `lucide-svelte`; devDeps: `typescript`, `tailwindcss@^4`, `@tailwindcss/vite`, `vite@^8`, `@sveltejs/vite-plugin-svelte@^7`, `vitest@^3`, `prettier`, `prettier-plugin-svelte`, `svelte-check`
- `sveltekit_template/svelte.config.js` — `adapter-static` with `vitePreprocess()`, `fallback: 'index.html'`
- `sveltekit_template/vite.config.ts` — `tailwindcss()` + `sveltekit()` plugins
- `sveltekit_template/tsconfig.json` — strict TypeScript config extending `.svelte-kit/tsconfig.json`
- `sveltekit_template/src/app.html` — SvelteKit shell with `%sveltekit.head%` and `%sveltekit.body%`
- `sveltekit_template/src/app.css` — Tailwind v4 `@import 'tailwindcss'`

### Verified

- `pnpm install && pnpm build` succeeds in `sveltekit_template/` (vite 8.0.8, adapter-static output to `build/`)

## [0.12.0] - 2026-04-15

### Added

- `src/learningfoundry/generator.py` — `generate_app()`: atomically copies `sveltekit_template/` to output dir, writes `curriculum.json` to `static/`; overwrites with warning; raises `GenerationError` if template is missing
- `sveltekit_template/package.json`, `sveltekit_template/svelte.config.js` — minimal template stubs (expanded in D.a)
- `tests/test_generator.py` — 11 tests covering output structure, `curriculum.json` content, overwrite behavior, and missing template

### Fixed

- `tests/test_exceptions.py` — added `teardown_method` to `TestLoggingSetup` to restore `learningfoundry` logger state, fixing `caplog` interference in cross-module test runs

## [0.11.0] - 2026-04-15

### Added

- `src/learningfoundry/pipeline.py` — `run_build()`, `run_validate()`, `run_preview()` orchestrating parse → resolve → generate; `run_validate()` returns `(bool, list[str])` without generating; `run_preview()` runs `pnpm install` + `pnpm run dev`
- `tests/test_pipeline.py` — 11 tests covering end-to-end build, generator injection, error propagation, validate-only mode, and error capture
- `tests/fixtures/content/mod-01/lesson-01.md`, `tests/fixtures/content/mod-02/lesson-02.md` — stub markdown content for fixture curriculum

## [0.10.0] - 2026-04-15

### Added

- `src/learningfoundry/resolver.py` — `resolve_curriculum()` with `ResolvedCurriculum`, `ResolvedModule`, `ResolvedLesson`, `ResolvedContentBlock` dataclasses; resolves text (markdown read), video (URL pass-through), quiz/exercise/visualization (provider delegation), and pre/post assessments; raises `ContentResolutionError` with block location context
- `tests/test_resolver.py` — 16 tests covering all block types, missing files, empty markdown warning, provider delegation, error wrapping with location, and assessment resolution

## [0.9.0] - 2026-04-15

### Added

- `src/learningfoundry/integrations/quizazz.py` — `QuizazzProvider` delegating to `quizazz_builder.compile_assessment()`; wraps all errors in `IntegrationError`; raises `ImportError` with install instructions if `quizazz-builder` is not installed
- `tests/test_integrations/test_quizazz.py` — 8 tests covering delegation, return value, error wrapping, error chaining, and missing package

## [0.8.0] - 2026-04-15

### Added

- `src/learningfoundry/integrations/__init__.py` — integrations package
- `src/learningfoundry/integrations/protocols.py` — `QuizProvider`, `ExerciseProvider`, `VisualizationProvider` Protocol classes
- `src/learningfoundry/integrations/nbfoundry_stub.py` — `NbfoundryStub` returning placeholder `ExerciseContent` dict with `"status": "stub"`
- `src/learningfoundry/integrations/d3foundry_stub.py` — `D3foundryStub` returning placeholder `VisualizationContent` dict with `"status": "stub"`
- `tests/test_integrations/test_nbfoundry_stub.py` — 12 tests verifying stub structure matches `ExerciseContent` TypeScript interface
- `tests/test_integrations/test_d3foundry_stub.py` — 13 tests verifying stub structure matches `VisualizationContent` TypeScript interface

## [0.7.0] - 2026-04-15

### Added

- `src/learningfoundry/parser.py` — `parse_curriculum()` and `_dispatch_parser()`: loads YAML, extracts version, dispatches to schema, raises `CurriculumVersionError` / `CurriculumValidationError` on failure
- `tests/test_parser.py` — 13 tests covering valid parsing, missing/null/unsupported/malformed version, malformed YAML, schema errors, and missing file

## [0.6.0] - 2026-04-15

### Added

- `src/learningfoundry/schema_v1.py` — Pydantic v1 curriculum schema: all block types (`TextBlock`, `VideoBlock`, `QuizBlock`, `ExerciseBlock`, `VisualizationBlock`), `Lesson`, `Module`, `CurriculumDef`, `CurriculumV1` with validators for IDs, YouTube URLs, uniqueness, and minimum counts
- `tests/fixtures/valid-curriculum.yml` — full fixture curriculum exercising all block types and assessments
- `tests/test_schema_v1.py` — 35 tests covering valid parsing, all block types, invalid URLs, ID format, duplicate IDs, and missing required fields

## [0.5.0] - 2026-04-15

### Added

- `src/learningfoundry/config.py` — `LoggingConfig`, `AppConfig` dataclasses and `load_config()` with CLI > config file > defaults precedence
- `tests/test_config.py` — 16 tests covering defaults, file overrides, CLI overrides, malformed YAML, and unknown key warnings

## [0.4.0] - 2026-04-15

### Added

- `src/learningfoundry/exceptions.py` — full exception hierarchy: `LearningFoundryError`, `ConfigError`, `CurriculumVersionError`, `CurriculumValidationError`, `ContentResolutionError`, `IntegrationError`, `GenerationError`
- `src/learningfoundry/logging_config.py` — `setup_logging(level, output)` using stdlib `logging`
- `tests/test_exceptions.py` — 17 tests covering hierarchy, string representations, and logging setup

## [0.3.0] - 2026-04-15

### Added

- `scripts/spike_e2e.py` — throwaway end-to-end spike: YAML parse → content resolve → SvelteKit skeleton generation
- `scripts/fixtures/spike-curriculum.yml` — minimal 1-module/1-lesson fixture curriculum
- `scripts/fixtures/content/lesson-01.md` — stub markdown content for the spike

## [0.2.0] - 2026-04-15

### Added

- `.github/workflows/publish.yml` — publishes sdist + wheel to PyPI on `v*` tag push via OIDC trusted publishing

## [0.1.0] - 2026-04-15

### Added

- `src/learningfoundry/__init__.py` with `__version__ = "0.1.0"`
- `src/learningfoundry/py.typed` PEP 561 marker
- `src/learningfoundry/cli.py` Click entry point with `--version` flag
- `src/learningfoundry/__main__.py` enabling `python -m learningfoundry`
