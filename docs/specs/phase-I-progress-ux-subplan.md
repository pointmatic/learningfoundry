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

## Story Map

| Story | Version | Title | Focus |
|-------|---------|-------|-------|
| I.f | v0.41.0 | Sidebar and Navigation Bug Fixes | Finish→dashboard, expand/contract fix, active highlight, progress refresh |
| I.g | v0.42.0 | Block Completion Events and Lesson Auto-Complete | Block events, button gating, revisit behavior |
| I.h | v0.43.0 | Curriculum Progress Bar | Dashboard total-progress bar, reactive store |
| I.i | v0.44.0 | Locking Configuration Schema | Python schema, resolver, config |
| I.j | v0.45.0 | Locking and Unlocking UI | Frontend locked state, unlock cascade, optional lessons |
