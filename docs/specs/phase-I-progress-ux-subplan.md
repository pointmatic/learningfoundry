# Phase I Sub-Plan: Progress Accounting and UX

> Sub-plan for Phase I (Functional and UX Improvements).
> Covers block-level completion events, lesson auto-complete, progress reactivity,
> sidebar/navigation bug fixes, curriculum-level progress display, and the
> content locking/unlocking system.
> Corresponds to stories I.f – I.j in `stories.md`.

---

## Gap Analysis

### What Exists

| Component | State |
|-----------|-------|
| `progress.ts` | `markLessonInProgress`, `markLessonComplete`, `getModuleProgress` exist |
| `LessonView.svelte` | Calls `markLessonInProgress` on mount; calls `markLessonComplete` via `onComplete` callback |
| `Navigation.svelte` | Next → `navigateTo()` directly (bypasses `onComplete`); Finish → `onComplete?.()` which does nothing (no handler in `+page.svelte`) |
| `ModuleList.svelte` | Expand/contract button wired but `$effect` immediately reverts manual toggles (self-dependency bug) |
| `LessonList.svelte` | Status icons (`✓ … ○`) rendered but progress never refreshes during session |
| `+layout.svelte` | Fetches module progress once on curriculum load; no live-update mechanism |
| `ProgressDashboard.svelte` | Per-module progress bars; no curriculum-level bar |
| `QuizBlock.svelte` | `QuizCompleteEvent` fires on quiz completion; score recorded to `quiz_scores` |
| `types/index.ts` | `LessonStatus`, `ModuleProgress`, `CurriculumProgress` typed |

### What's Missing

- Block-level completion events for text and video blocks
- Lesson completion driven by block events (not navigation click)
- Next/Finish button gating on per-lesson completion state
- Immediate button activation when revisiting an already-completed lesson
- `pass_threshold` support on quiz blocks
- Reactive progress refresh during a session (sidebar and dashboard)
- Sidebar expand/contract fix (the `$effect` self-dependency)
- Active module visual highlight in sidebar
- Finish → dashboard navigation
- Curriculum-level progress bar on dashboard
- Locking configuration in Python schema and frontend evaluation
- `unlock_module_on_complete` lesson flag and cascade logic
- Optional lesson status and neutral indicator

---

## Feature Requirements

### FR-P1: Block Completion Events

Each content block independently reports when it has been sufficiently engaged with:

- **Text block** — fires `textcomplete` after the block has been **continuously visible in the viewport for 1 second** (Intersection Observer + 1 s debounce timer). If the block is in the viewport on initial render, the 1-second clock starts immediately.
- **Video block** — fires `videocomplete` on the **YouTube IFrame Player API `ENDED` event** (player state `0`). If the IFrame API is unavailable or signals an error, falls back to an Intersection Observer with a **3-second** continuous-in-viewport threshold.
- **Quiz block** — fires `quizcomplete` after the existing `QuizCompleteEvent` fires **and** `score / maxScore >= pass_threshold`. Default `pass_threshold = 0.0` (any quiz completion, regardless of score, fires the event). If the learner fails to meet the threshold, they can retry; the block fires on the first passing attempt.

`ContentBlock.svelte` is responsible for forwarding the per-block event up to `LessonView`.

### FR-P2: Lesson Auto-Complete and Button Gating

`LessonView.svelte` tracks which blocks have fired their completion events using a `Set<number>` keyed on block index.

**Completion cascade:**
1. Lesson mounts → `markLessonInProgress` (unchanged).
2. Each block fires its completion event → block index added to the completion set.
3. When the completion set size equals the total block count → `markLessonComplete` is called immediately; Next/Finish button activates.
4. User clicks Next/Finish → navigates (Next → next lesson; Finish → `/`).

**Revisit behavior:** On mount, if the lesson's current DB status is already `complete`, the completion set is pre-filled (all blocks treated as done) so the button is immediately active. Block events still fire normally if the learner re-engages — they are no-ops for gating purposes since the lesson is already complete.

**Edge case — zero blocks:** A lesson with no content blocks is treated as immediately complete on mount (completion set of 0 out of 0).

### FR-P3: Reactive Progress Updates

The one-shot progress fetch in `+layout.svelte` is replaced by a **writable reactive progress store** (`$lib/stores/progress.ts`). Any component that writes to the DB (lesson completion, quiz scores) also calls an `invalidateProgress()` helper that triggers a re-fetch. The sidebar module cards and the dashboard both subscribe to this store, so they update in real time without a page reload.

### FR-P4: Sidebar UX Fixes

**Expand/contract fix:** The `$effect` in `ModuleList.svelte` is refactored to track the *last auto-expanded module* separately. Auto-expansion only fires when `currentPosition.moduleId` changes to a new value; it does not override subsequent manual toggles. Result: clicking any module header correctly expands/collapses it.

**Active module highlight:** The module card containing the currently active lesson receives a distinct left-border accent and background tint (e.g., `border-l-2 border-blue-500 bg-blue-50`).

**Finish → dashboard:** The `oncomplete` handler in `+page.svelte` calls `goto('/')` so Finish navigates the learner to the dashboard.

### FR-P5: Curriculum Progress Bar

The dashboard page (`/`) shows a single curriculum-level progress bar above the module cards:

```
12 of 40 lessons completed   [████████░░░░░░░░░░░░]
```

Computed from the reactive progress store as `sum(complete lessons) / sum(all lessons)`. Updates live as lessons are completed.

### FR-P6: Content Locking

Sequential access control is configurable at three levels; the **most local setting wins**:

| Level | Location | Fields |
|-------|----------|--------|
| Global | `~/.config/learningfoundry/config.yml` | `locking.sequential`, `locking.lesson_sequential` |
| Curriculum | `curriculum.yml` top-level `locking:` block | same fields |
| Module | per-module `locked: true/false` | boolean override |

**Module-level sequential (`sequential: true`):** Module N+1 is accessible only after all lessons in module N are `complete`. A locked module cannot be expanded in the sidebar; its lesson list is never shown. The module card displays a lock icon.

**Lesson-level sequential (`lesson_sequential: true`):** Within a module, lesson N+1 is accessible only after lesson N is `complete`. A locked lesson in the sidebar is non-interactive (cursor not-allowed, muted styling, no lock icon needed — context makes it clear).

**Default:** both `sequential` and `lesson_sequential` default to `false` (no locking). An absent `locking:` key at any level inherits from the next-outer level.

### FR-P7: Module Unlock by Lesson (`unlock_module_on_complete`)

A lesson may carry `unlock_module_on_complete: true`. When that lesson's auto-complete fires:

1. **Same-module siblings** — all other lessons in the module transition from locked to **optional** (accessible but not required for module completion). The sidebar shows them with a neutral indicator (`◇`), distinct from `not_started` (`○`), `in_progress` (`…`), and `complete` (`✓`).
2. **Next module** — the immediately following module in the curriculum sequence is unlocked, making it expandable and navigable regardless of module-sequential locking state.

**Optional lesson semantics:** An optional lesson's completion contributes to the curriculum-level progress bar and the module progress bar, but its incomplete status does not block module completion. Module completion is determined by: all non-optional lessons are `complete` (or the module contains no non-optional lessons).

**Unlock derivation (frontend, no extra DB table):** The optional/locked state is computed at runtime from the curriculum config (which lesson is the unlock key) + the reactive progress store (is that key lesson complete?). No new DB schema is required.

### FR-P8: Quiz Pass Threshold

`QuizBlock` content type adds an optional `pass_threshold: float` (range 0.0–1.0, default 0.0). The field is set in `curriculum.yml` on the quiz content block:

```yaml
- type: quiz
  source: quizazz
  ref: assessments/mod-01-post.yml
  pass_threshold: 0.7   # optional; default 0.0
```

The threshold is passed through the Python resolver into `curriculum.json` and consumed by the frontend `QuizBlock` wrapper. When `QuizCompleteEvent` fires, the wrapper checks `score / maxScore >= pass_threshold` before emitting the block-level `quizcomplete` event. A failed attempt produces no block-complete event; quizazz handles retry internally.

---

## Technical Changes

### Python pipeline

| File | Change |
|------|--------|
| `schema_v1.py` | `QuizBlock` gains `pass_threshold: float = 0.0`; `LessonSchema` gains `unlock_module_on_complete: bool = False`; new `LockingConfig(sequential, lesson_sequential)` model; `ModuleSchema` gains `locked: Optional[bool]`; curriculum top-level gains `locking: Optional[LockingConfig]` |
| `resolver.py` | Pass through `pass_threshold`, `unlock_module_on_complete`, `locked`, and resolved `locking` config into `ResolvedCurriculum` / `curriculum.json` |
| `config.py` | Add `locking: LockingConfig` block to global config schema with defaults `sequential=False, lesson_sequential=False` |
| `tests/test_schema_v1.py` | New cases: `pass_threshold` round-trips; `unlock_module_on_complete` round-trips; `LockingConfig` defaults and override; `locked` per-module |
| `tests/test_resolver.py` | Locking fields appear in resolved curriculum output |
| `tests/test_smoke_sveltekit.py` | `curriculum.json` carries locking config |

### TypeScript / SvelteKit template

| File | Change |
|------|--------|
| `types/index.ts` | `LessonStatus` adds `'optional'`; `Lesson` adds `unlockModuleOnComplete?: boolean`; `Module` adds `locked?: boolean`; `Curriculum` adds `locking?: LockingConfig`; `QuizContent` adds `passThreshold?: number`; new `LockingConfig` interface |
| `stores/progress.ts` (new) | Writable reactive progress store + `invalidateProgress()` helper; replaces one-shot `getModuleProgress` call in `+layout.svelte` |
| `utils/locking.ts` (new) | Pure functions: `isModuleLocked(curriculum, progress, moduleId)`, `isLessonLocked(curriculum, progress, moduleId, lessonId)`, `getOptionalLessons(curriculum, progress, moduleId)` |
| `TextBlock.svelte` | Intersection Observer + 1 s debounce; dispatches `textcomplete` |
| `VideoBlock.svelte` | YouTube IFrame Player API `onStateChange` (state 0 = ENDED) → `videocomplete`; 3 s viewport fallback |
| `ContentBlock.svelte` | Forwards `textcomplete`, `videocomplete`, `quizcomplete` to parent as unified `blockcomplete` with block index |
| `LessonView.svelte` | Tracks block completion set; all-complete → `markLessonComplete` + `invalidateProgress()`; passes `disabled` to `Navigation`; pre-fills set on mount if lesson already `complete` |
| `Navigation.svelte` | Accepts `disabled: boolean` prop; styles disabled state; Finish calls `oncomplete` (which navigates to `/`) |
| `+page.svelte` | Passes `oncomplete={() => goto('/')}` to `LessonView` |
| `+layout.svelte` | Subscribes to reactive progress store instead of one-shot fetch |
| `ModuleList.svelte` | Fix `$effect` (track `lastAutoExpandedModule` separately; don't re-run on `expandedModuleId` change); active module highlight; locked module: no expand, lock icon |
| `LessonList.svelte` | `optional` status → `◇` neutral icon; locked lesson → non-interactive |
| `ProgressDashboard.svelte` | Curriculum-level progress bar above module cards |

### Deferred (documented, not implemented)

- **Reset button** (course / module / lesson): defined, deferred to a future story.
- **Per-lesson scroll memory** on revisit (deferred from Story I.b).
- **Non-YouTube video providers**: the IFrame API path is YouTube-specific; other providers use the viewport fallback until their own story.

---

## Out of Scope

- Reset button implementation
- Per-lesson scroll position memory
- Cross-tab progress sync
- Progress export/import
- Adaptive sequencing beyond sequential locking

---

## Discovered Post-Shipping (after v0.45.0)

Three independent user-visible bugs reproduced consistently against any multi-lesson curriculum with at least one video block:

1. **No progress is ever recorded** — no checkmarks in the sidebar, no module % advancement, no curriculum-level progress bar movement, regardless of how long the learner spends in lessons or how many they "finish."
2. **Next/Finish is deactivated when revisiting a previously completed lesson** — the button does not honour the FR-P2 "if already `complete`, pre-fill set so button is immediately active" contract.
3. **Old video block remains visible when navigating between two lessons that both contain a `video` block** — the new lesson's URL is silently ignored and the original player keeps playing.

### Root cause

A single navigation defect in `Navigation.goNext()` and `LessonList.handleClick()` cascades into all three symptoms. The Story I.g task list specifies that `Navigation.goNext()` calls `navigateTo(next.moduleId, next.lessonId)`, and `LessonList.handleClick()` does the same on sidebar lesson clicks. But `navigateTo` is the *curriculum-store* helper at `stores/curriculum.ts` — it sets `currentPosition` and nothing else. The lesson route `[module]/[lesson]/+page.svelte` derives the rendered lesson from `page.params`, not from `currentPosition`. So in-app "navigation" updates the sidebar highlight and the `nextLesson` / `previousLesson` derived stores, but **the URL never changes** and `LessonView` is never re-mounted for the next lesson. The user stays on whichever lesson they originally landed on directly.

This single defect produces all three bugs:

- **Bug 1** — `LessonView.onMount` is the only call site for `markLessonInProgress` and the only path that reads existing lesson progress to pre-fill state. Because the component never re-mounts, only the very first lesson the user reaches by direct URL ever fires `markLessonInProgress`. If that lesson is not visibly engaged with long enough to trigger every block's completion event, `markLessonComplete` is also never called. Nothing is ever written to `lesson_progress` and the entire downstream progress UX (sidebar checkmarks, module bars, curriculum bar) sits at zero forever.
- **Bug 2** — `allBlocksComplete` and `completedBlocks` are component-instance state. They become *sticky* across "navigations": once any lesson has fired all its block events, `allBlocksComplete` is `true` for every subsequent lesson the user reaches, until they hard-refresh. Conversely, the FR-P2 revisit pre-fill never gets a chance to run on a re-mount because there is no re-mount.
- **Bug 3** — even after the navigation defect is fixed and `LessonView` re-mounts, a latent issue remains in [LessonView.svelte:68](../../sveltekit_template/src/lib/components/LessonView.svelte#L68): `{#each lesson.content_blocks as block, i (i)}` keys by index, so any future flow that swaps blocks while `LessonView` stays mounted will reuse the same `<VideoBlock>` instance with new `block` props. `VideoBlock` has no `$effect` watching `content.url`, so the player is never destroyed/recreated. The new URL is silently ignored. (This is what was actually observed before the navigation fix, because the same `LessonView` was being asked to show a new lesson's blocks via prop change rather than re-mount.)

### Why the v0.41–0.45 test harness did not catch this

- **Vitest tests with `$app/navigation` mocked.** Stories I.f and I.g specified tests that mock `goto` (e.g. *"Test: Finish button calls `goto('/')` on last lesson (mock `$app/navigation`)"*). These tests assert that the *navigation function is called* — they do not assert that the *rendered lesson swapped* or that the URL changed. A mocked `goto` hides the absence of a real call.
- **No assertion on the `goNext` → URL effect link.** The Story I.g `LessonView.test.ts` task asserted button-disabled gating and `markLessonComplete` invocation but did not exercise the `<Navigation>` button's `onclick` and observe that the next lesson actually rendered.
- **No end-to-end harness.** There is no Playwright (or equivalent) browser test in the template, so the cascade from "click Next" → URL change → `+page.svelte` re-derivation → `LessonView` re-mount → `markLessonInProgress` for the new lesson was never exercised end-to-end.

### Plan delta

Two new feature requirements complete the navigation/lifecycle contract that FR-P2 implicitly assumed, plus a test-harness requirement. They are added below; Story I.k implements all three.

### FR-P9: Lesson Navigation Actually Changes the URL

In-app lesson navigation must update the SvelteKit URL (`/${moduleId}/${lessonId}`) so the lesson route re-derives `lesson` and `module` from `page.params` and `LessonView` re-mounts. The `currentPosition` store remains the source of truth for "which lesson is highlighted" but stops being a parallel routing mechanism.

- `Navigation.goNext()`: `if (next) goto(\`/${next.moduleId}/${next.lessonId}\`); else goto('/')`.
- `Navigation.goPrev()`: `if (prev) goto(\`/${prev.moduleId}/${prev.lessonId}\`)`.
- `LessonList.handleClick(lessonId)`: `goto(\`/${moduleId}/${lessonId}\`)` (replacing the bare `navigateTo` call).
- `ProgressDashboard.resumeFirst(mod)`: `goto(\`/${mod.id}/${target.id}\`)`.
- `currentPosition` is updated as a side effect of route changes (the existing `$effect` in `[module]/[lesson]/+page.svelte` already does this — no new wiring needed).
- `navigateTo()` is kept for places where store-only updates are intentional (none currently exist; the helper becomes a thin wrapper used only by the route's URL→store sync). Alternatively, rename it to `setPositionFromRoute()` to remove the foot-gun name; chosen approach is at the implementor's discretion.

### FR-P10: Component Lifecycle Invariants for Lesson and Block Swaps

Codify the lifecycle contracts that FR-P2 and I.g assumed but never enforced:

- **LessonView re-mounts per lesson.** Either via the route naturally tearing down `[module]/[lesson]/+page.svelte`'s subtree on URL change (the SvelteKit-default behaviour once FR-P9 is in place), or explicitly via `{#key lesson.id}<LessonView … />{/key}` in `+page.svelte`. The chosen mechanism must guarantee `onMount` runs for each distinct `(moduleId, lessonId)` the learner reaches.
- **Content block iteration keys on identity, not index.** `LessonView`'s `{#each}` keys on a stable per-block identity (e.g. `block.ref ?? block.url ?? \`${block.type}-${i}\``). The intent: when blocks are added, removed, or have their content swapped, Svelte tears down the right instances and creates new ones rather than reusing slots.
- **VideoBlock reacts to `content.url` changes.** Even with a stable iteration key, `VideoBlock` carries an `$effect` that destroys and re-creates the YouTube player when `content.url` changes within the same component instance. This keeps the player aligned with its content if the parent ever does choose to update props in place.

### FR-P11: End-to-End Test Harness

Introduce Playwright (or a comparably realistic harness) in `sveltekit_template/` to exercise the routing + lifecycle cascade that vitest with mocked `$app/navigation` cannot reach. Smoke tests must include:

- Sidebar lesson click → URL updates → new lesson title rendered.
- Next button on a complete lesson → URL advances by one in `lessonSequence` order.
- Lesson visibly engaged for long enough to fire all block events → checkmark appears in sidebar and module % advances, *without* a page reload.
- Returning to a previously completed lesson via sidebar click → Next/Finish enabled immediately.
- Two lessons with `video` blocks at the same index → only the new video's iframe is in the DOM after navigation.

The harness lives in `sveltekit_template/e2e/` and runs against the built static site (`pnpm build && pnpm preview`) or `pnpm dev`. It is invoked from the smoke pipeline so `tests/test_smoke_sveltekit.py` fails on regression.

---

## Story Map

| Story | Version | Title | Focus |
|-------|---------|-------|-------|
| I.f | v0.41.0 | Sidebar and Navigation Bug Fixes | Finish→dashboard, expand/contract fix, active highlight, progress refresh |
| I.g | v0.42.0 | Block Completion Events and Lesson Auto-Complete | Block events, button gating, revisit behavior |
| I.h | v0.43.0 | Curriculum Progress Bar | Dashboard total-progress bar, reactive store |
| I.i | v0.44.0 | Locking Configuration Schema | Python schema, resolver, config |
| I.j | v0.45.0 | Locking and Unlocking UI | Frontend locked state, unlock cascade, optional lessons |
| I.k | v0.46.0 | Lesson Navigation Lifecycle Fix and E2E Harness | FR-P9, FR-P10, FR-P11 — discovered post-shipping |
