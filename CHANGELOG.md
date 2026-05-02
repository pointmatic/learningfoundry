# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
