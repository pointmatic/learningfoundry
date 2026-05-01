# stories.md -- learningfoundry (python)

This document breaks the `learningfoundry` project into an ordered sequence of small, independently completable stories grouped into phases. Each story has a checklist of concrete tasks. Stories are organized by phase and reference modules defined in `tech-spec.md`.

Stories with code changes include a version number (e.g., v0.1.0). Stories with only documentation or polish changes omit the version number. The version follows semantic versioning and is bumped per story. Stories are marked with `[Planned]` initially and changed to `[Done]` when completed.

For a high-level concept (why), see `concept.md`. For requirements and behavior (what), see `features.md`. For implementation details (how), see `tech-spec.md`. For project-specific must-know facts, see `project-essentials.md` (`plan_phase` appends new facts per phase).

---

## Phase I: Functional and UX Improvements

---

### Story I.a: v0.37.0 Local Image Support — Co-located Assets and Markdown Rewriting [Done]

learningfoundry has no first-class image support. Authors today have only two options, both bad:
- Use absolute CDN URLs (`![](https://cdn.example.com/foo.png)`) — works at runtime, but couples curriculum content to external infrastructure and breaks for offline / pre-publish iteration.
- Hand-drop files into `sveltekit_template/static/` — wrong layer (the template is the project-wide source of truth, not a per-curriculum asset bag), and `static/` is not in `_PRESERVED_PATHS`, so any drop gets blown away on the next `learningfoundry build`.

The desired UX is **co-location** — authors keep images alongside the markdown files that reference them, the same way they would in any other documentation system:

```
my-curriculum/
  curriculum.yml
  content/
    mod-01/
      lesson-01.md
      lesson-01-figures/
        diagram.png
        screenshot-1.png
```

In `lesson-01.md`:
```markdown
![Architecture overview](lesson-01-figures/diagram.png)
```

The pipeline detects the relative image reference, copies the asset into the generated SvelteKit project at a deterministic location, and rewrites the markdown URL to an absolute path that resolves at any nested route. CDN/absolute URLs (`https://...`, `http://...`, protocol-relative `//...`, and any URL starting with `/`) pass through unchanged.

**Resolution semantics:**
- Image paths are resolved relative to the markdown file's directory (not `base_dir`, not the curriculum file's location). `![](figures/foo.png)` in `content/mod-01/lesson-01.md` resolves to `content/mod-01/figures/foo.png` on disk.
- Missing image files raise `ContentResolutionError` with the lesson location in the message (consistent with the existing pattern for missing markdown text refs).
- Each unique source image is copied exactly once even if referenced by multiple lessons — the destination path is content-keyed (`static/content/<sha256[:12]>/<basename>`) so duplicates dedupe automatically.
- The rewritten markdown URL is `/content/<sha256[:12]>/<basename>` — absolute, so it works at `/`, `/mod-01/`, `/mod-01/lesson-01/`, etc.
- `static/content/` is added to `_PRESERVED_PATHS` so re-builds don't re-copy unchanged assets.

**Out of scope (deferred to a follow-up story):**
- Dedicated `type: image` content block (caption, sizing, lazy-load attributes, first-class alt text). Markdown `![alt](path)` covers 80% of cases; a dedicated block is its own design problem.
- Image optimisation / responsive `srcset` generation. The pipeline copies bytes verbatim for v0.37.0.
- Video / audio / other binary asset types. Same pattern would apply but each is its own story.

**Tasks:**

- [x] Create `src/learningfoundry/asset_resolver.py` — pure function `resolve_markdown_assets(markdown: str, markdown_path: Path) -> tuple[str, list[Asset]]`:
  - [x] Walk the markdown text for `![alt](path)` and the rarer `<img src="path">` HTML form
  - [x] Skip absolute URLs (`http://`, `https://`, `//`, leading `/`, `data:` URIs, mailto/tel)
  - [x] Resolve relative paths against `markdown_path.parent`; raise `ContentResolutionError` for missing files
  - [x] Compute `sha256` of source bytes, take first 12 hex chars
  - [x] Return rewritten markdown + list of `Asset(source: Path, dest_relative: str)` records where `dest_relative` is `content/<hash12>/<basename>`
- [x] Update `src/learningfoundry/resolver.py`:
  - [x] `ResolvedTextBlock` gains `assets: list[Asset]` field (default `[]`)
  - [x] `_resolve_text_block()` calls `resolve_markdown_assets()` and stores both the rewritten markdown and the asset list
- [x] Update `src/learningfoundry/generator.py`:
  - [x] After `_atomic_copy()`, walk the resolved curriculum collecting all `Asset` records and copy each `source` to `output_dir / "static" / asset.dest_relative` (skip if dest already exists with matching size — the hash in the path makes this safe)
  - [x] Add `"static/content"` to `_PRESERVED_PATHS` so subsequent rebuilds preserve already-copied assets
- [x] `src/learningfoundry/exceptions.py` — confirm `ContentResolutionError` is the right type for missing images (it is — same family as missing markdown text refs)
- [x] `tests/test_asset_resolver.py` (new):
  - [x] Relative image ref → resolved path + rewritten URL
  - [x] Absolute URL passthrough (`https://`, `http://`, `//`, leading `/`)
  - [x] `data:` URI passthrough
  - [x] Missing image raises `ContentResolutionError` with markdown path in message
  - [x] Multiple references to same image → deduped (one Asset, two rewrites pointing at same dest)
  - [x] HTML `<img src="...">` form alongside markdown `![]()` form
  - [x] Path traversal attempt (`../../../etc/passwd`) — either rejected or resolves to a path that's normalised within the curriculum tree (decide based on what's safest)
- [x] `tests/test_resolver.py` — new cases: text block with images populates `ResolvedTextBlock.assets`; missing image raises `ContentResolutionError` with lesson location
- [x] `tests/test_generator.py` — new cases: assets land in `output_dir/static/content/<hash>/<basename>`; `static/content/` is in `_PRESERVED_PATHS`; rebuild does not re-copy unchanged assets
- [x] `tests/test_smoke_sveltekit.py` — extend the all-block-types fixture with a co-located image; assert it appears in the smoke-built site's `static/content/` directory
- [x] `docs/specs/features.md` updates:
  - [x] **Inputs → Markdown content files** (~line 114): document the image co-location convention. Authors place image files alongside the markdown that references them; relative paths in `![alt](path)` and `<img src="path">` are resolved against the markdown file's directory. Absolute URLs (`https://`, `http://`, `//`, leading `/`, `data:`) pass through unchanged.
  - [x] **Outputs → Static SvelteKit application** (~line 138): mention the generated `static/content/<hash12>/<basename>` directory containing copied image assets, served at `/content/...`.
  - [x] **FR-2: Content Resolution** (~line 176): extend with an "Image asset resolution" sub-requirement — the resolver scans every text block's markdown for image refs, hashes each unique source file, records `(source, dest_relative)` pairs on `ResolvedTextBlock.assets`, and rewrites the markdown to use absolute `/content/<hash12>/<basename>` URLs. Missing image files raise `ContentResolutionError` with the lesson location.
- [x] `docs/specs/tech-spec.md` updates:
  - [x] **Package Structure** (~line 88): add `src/learningfoundry/asset_resolver.py` to the module list with a one-line description.
  - [x] **Key Component Design** — add a new `### asset_resolver.py — Markdown Image Asset Resolution` subsection between `resolver.py` (~line 385) and `integrations/protocols.py` (~line 442). Document: public API (`resolve_markdown_assets()`, `Asset` dataclass), the regex strategy for `![alt](path)` and `<img src="...">`, fenced-code-block skipping, absolute-URL passthrough rules, hash-based dedup convention (`sha256[:12]`), and `ContentResolutionError` semantics.
  - [x] **`resolver.py` — Content Resolution** (~line 385): update the section to note that text-block resolution now includes calling `resolve_markdown_assets()`, and `ResolvedTextBlock` carries the resolved markdown plus an `assets: list[Asset]` field.
  - [x] **`generator.py` — SvelteKit Project Generation** (~line 613): document the new asset-copy step (after `_atomic_copy()`, walk the resolved curriculum collecting `Asset` records and copy each into `static/content/<hash12>/<basename>`); document the extension of `_PRESERVED_PATHS` to include `static/content`.
  - [x] **Data Models → Resolved Curriculum** (~line 710): add `assets: list[Asset]` to the `ResolvedTextBlock` description and define the `Asset` dataclass shape (`source: Path`, `dest_relative: str`).
- [x] `README.md` — new "Images and assets" section under Curriculum YAML Format documenting the co-location pattern, the `/content/<hash>/<file>` rewrite, and that absolute URLs pass through. Mention that for production CDN deploys, authors can simply use absolute URLs in markdown — no learningfoundry change needed.
- [x] Bump version to v0.37.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`
- [x] Update `CHANGELOG.md` with v0.37.0 entry under Added (image asset pipeline) and Changed (`_PRESERVED_PATHS` extended)
- [x] Verify: `pyve test` passes, `pyve test -m smoke` passes, `ruff` and `mypy` clean

---

### Story I.c: Lesson Title vs Markdown H1 — Authoring Convention [Done]

The generated lesson page renders the curriculum-yml `lesson.title` in a layout `<h1>` (`LessonView.svelte`) and then renders the markdown body — including the markdown's own `# Heading` — as an inline `<h1>` (via `marked` inside `TextBlock.svelte`'s `prose` block). When authors give both the same string the page shows the same title twice, looking duplicative and broken; as a side effect the page also has two `<h1>` elements which is poor for screen readers and SEO. There is no rendering bug — it is an authoring convention we never wrote down. Document the convention so authors avoid the trap from day one.

**Recommended convention:**
- `lesson.title` in `curriculum.yml` → short, navigation-shaped. Either a number (`"3"`), a label (`"Lesson 3"`), or label-plus-abbreviation (`"Lesson 3: Cultural Diffusion"`). This is the string that appears in the sidebar, the breadcrumb, the browser tab title, and the page header.
- Markdown `# Heading` → the descriptive long-form title that complements (does not echo) the lesson title. Picture them on one line separated by a colon: `<lesson.title>: <markdown H1>` should read naturally and contain no repeated words.
- Authors who genuinely have nothing to add in an H1 should omit the markdown `#` heading entirely and start the lesson with body prose. The layout `<h1>` already serves as the page title.

**Out of scope (deferred to a follow-up story if the convention is not enough):**
- Auto-detecting and demoting/eliminating a markdown leading `# H1` that matches `lesson.title`. Conventions are cheaper than enforcement; let's see if docs solve it before adding code.
- Switching the layout `<h1>` to an `<h2>` so the markdown can own the page-level `<h1>`. Bigger semantic restructure; needs its own story.

**Tasks:**

- [x] `README.md` — new "Lesson titles and markdown headings" subsection under Curriculum YAML Format. Explain the two-headings situation (one from `curriculum.yml`, one from the markdown body), the recommended pattern (short navigational title in YAML, descriptive long-form `# H1` in the markdown), a good/bad side-by-side example, and the "just omit the H1" escape hatch. Add the new subsection to the Table of Contents.
- [x] `docs/specs/features.md` — under **Inputs → Markdown content files**, add a one-paragraph cross-reference to the README convention so a future LLM reading the spec sees it.
- [x] Mark Story I.c Done. No version bump (docs-only). No CHANGELOG entry (Keep-a-Changelog ties to versions).

---

### Story I.b: v0.38.0 Reset Main Scroll on Lesson Navigation [Done]

The lesson layout puts a fixed-height shell (`h-screen overflow-hidden`) with two inner scroll containers — a sidebar `<aside>` and a content `<main>` (`+layout.svelte`). SvelteKit's built-in scroll restoration only manages `window.scrollY`, so navigating from the bottom of one lesson (where the Next button lives) to the next lesson leaves `<main>` scrolled to the bottom — the new page renders, but the user lands at the footer of the lesson and has to manually scroll up to see the lesson title. Same root cause when clicking a lesson in the sidebar from the middle of the previous lesson.

**Fix:** register an `afterNavigate` hook in `+layout.svelte` that resets the `<main>` element's `scrollTop` to `0` on every forward (non-`popstate`) navigation. Skipping `popstate` preserves the browser's natural back/forward scroll-restoration UX so a user pressing Back lands where they were before clicking through.

**Out of scope (deferred to a follow-up story):**
- Per-lesson scroll memory (revisiting a partially-read lesson lands where you left off). Needs a per-lesson scroll-position store keyed on `(moduleId, lessonId)`.
- Smooth-scroll animation on reset. The instant default is fine for forward nav.

**Tasks:**

- [x] `src/learningfoundry/sveltekit_template/src/routes/+layout.svelte`:
  - [x] `bind:this={mainEl}` on the existing `<main>` element
  - [x] Import `afterNavigate` from `$app/navigation`
  - [x] Register `afterNavigate(({ type }) => { if (mainEl && type !== 'popstate') mainEl.scrollTop = 0; })`
- [x] `src/learningfoundry/sveltekit_template/src/routes/layout.test.ts` (new): vitest unit test that verifies the `afterNavigate` callback resets `scrollTop` to `0` for forward navigations and leaves it alone for `popstate`. Mock `$app/navigation`'s `afterNavigate` to capture the registered callback, then exercise it with both navigation types against a stub element.
- [x] Bump version to v0.38.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] `CHANGELOG.md` — v0.38.0 entry under "Fixed".
- [x] Verify: `pyve test` passes, `pyve test tests/test_smoke_sveltekit.py` passes (covers `pnpm test` → vitest in the generated template), `ruff` and `mypy` clean.

---

### Story I.d: v0.39.0 Render Module Descriptions on Dashboard [Done]

`curriculum.yml` lets authors give each module a `description:` field; `schema_v1.py` defaults it to `""` and the resolver preserves it on `ResolvedModule`. The frontend `Module` TypeScript interface already declares `description: string`. But `ProgressDashboard.svelte` (the home page module cards) only rendered `mod.title` and the progress bar — descriptions were never shown.

**Fix:** render `mod.description` as muted body text under the module title row when non-empty.

**Tasks:**

- [x] `src/learningfoundry/sveltekit_template/src/lib/components/ProgressDashboard.svelte` — `{#if mod.description}` paragraph between title row and `<ProgressBar>`.
- [x] `tests/test_resolver.py` — `test_module_description_round_trips` with explicit YAML description.
- [x] `tests/test_smoke_sveltekit.py` — assert `build/curriculum.json` carries `modules[0].description == "First module."` and `modules[1]` has empty/missing description.
- [x] Bump version to v0.39.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] `CHANGELOG.md` — v0.39.0 under "Added".
- [x] Verify: `pyve test`, smoke, `ruff`, `mypy`.

**Out of scope:**

- `@testing-library/svelte` component tests (deferred).
- Markdown in module descriptions (plain strings only in v1).

---

### Story I.e: v0.40.0 Video 'provider' and 'extensions' [Done]

Video blocks only had a `url`; the frontend was hard-coded to YouTube. Authors need an explicit **player** field so new providers (Vimeo, self-hosted, …) can be added without reshaping the whole curriculum schema, and a **bag for player-specific options** (chapters, transcripts, autoplay flags) that cannot be normalized across all players.

**Design:**
- YAML / Pydantic: `provider: youtube` (default), `extensions: {}` arbitrary JSON-serializable dict, passed through resolver into `curriculum.json` unchanged.
- Resolver: validates URL against YouTube when `provider == youtube`; exports public `YOUTUBE_URL_RE` from `schema_v1` for a single regex source.
- Frontend: `VideoContent` gains optional `provider` and `extensions`; `VideoBlock.svelte` dispatches on `provider` (default `youtube`), documents extensions for future per-provider UI.

**Tasks:**

- [x] `schema_v1.py` — `VideoBlock` with `provider`, `extensions`, `model_validator` for URL-by-provider; export `YOUTUBE_URL_RE`.
- [x] `resolver.py` — emit `provider` + `extensions` in video `content`; import `YOUTUBE_URL_RE`.
- [x] `sveltekit_template` — `VideoContent` + `VideoBlock.svelte` provider dispatch; mirror workspace-root `sveltekit_template/`.
- [x] `tests/test_schema_v1.py`, `tests/test_resolver.py`, `tests/test_smoke_sveltekit.py` — coverage.
- [x] `README.md`, `docs/specs/features.md`, `docs/specs/tech-spec.md`.
- [x] Bump v0.40.0, `CHANGELOG.md`.

**Out of scope:** Implementing chapters/transcript UI, new providers, autoplay.

---

### Story I.f: v0.41.0 — Sidebar and Navigation Bug Fixes [Done]

Three independent bugs that have accumulated in the SvelteKit frontend. None require the new block-completion model — they can be fixed in isolation.

**Bug 1 — Finish does nothing on the last lesson.**
`+page.svelte` renders `<LessonView>` without an `oncomplete` prop. `handleNavComplete` in `LessonView` marks the lesson complete then calls `oncomplete?.()`, which is `undefined`. Fix: pass `oncomplete={() => goto('/')}` from `+page.svelte` so Finish navigates to the dashboard.

**Bug 2 — Sidebar expand/contract reverts immediately.**
`ModuleList.svelte`'s `$effect` reads `expandedModuleId` (a `$state`), creating a self-dependency. When a user clicks a module header to expand it, `expandedModuleId` changes → effect re-runs → sees it no longer matches `currentPosition.moduleId` → immediately reverts it. Fix: introduce `lastAutoExpandedModuleId` (a separate state variable); the effect only fires when `currentPosition.moduleId` changes to a new value, leaving manual toggles undisturbed.

**Bug 3 — No active module highlight.**
The module card for the module containing the current lesson has no visual distinction from inactive modules. Fix: apply a left-border accent and background tint when `mod.id === $currentPosition?.moduleId`.

**Tasks:**

- [x] `sveltekit_template/src/routes/[module]/[lesson]/+page.svelte`:
  - [x] Import `goto` from `$app/navigation`
  - [x] Pass `oncomplete={() => goto('/')}` to `<LessonView>`
- [x] `sveltekit_template/src/lib/components/ModuleList.svelte`:
  - [x] Introduce `let lastAutoExpandedModuleId = $state<string | null>(null)`
  - [x] Refactor `$effect`: only run the auto-expand when `pos.moduleId !== lastAutoExpandedModuleId`; set both `expandedModuleId` and `lastAutoExpandedModuleId` when auto-expanding
  - [x] Add active module highlight to the `<li>` element: `border-l-2 border-blue-500 bg-blue-50` when `mod.id === $currentPosition?.moduleId`
- [x] `sveltekit_template/src/routes/layout.test.ts` (new):
  - [x] Test: Finish button calls `goto('/')` on last lesson (mock `$app/navigation`)
  - [x] Test: clicking a non-current module header correctly expands it and keeps it expanded (effect does not revert the toggle)
  - [x] Test: auto-expand fires when `currentPosition.moduleId` changes to a new module
  - [x] Test: active-module CSS class applied to correct `<li>` only
- [x] Mirror all sveltekit_template changes to `src/learningfoundry/sveltekit_template/`
- [x] Bump version to v0.41.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`
- [x] `CHANGELOG.md` — v0.41.0 entry under "Fixed" (three items: Finish navigation, sidebar expand, active module highlight)
- [x] Verify: `pyve test`, `pyve test tests/test_smoke_sveltekit.py`, `ruff`, `mypy`

**Out of scope:**
- Reactive progress refresh during session (added in I.g alongside block completion)
- Per-lesson scroll memory on revisit

---

### Story I.g: v0.42.0 — Block Completion Events and Lesson Auto-Complete [Done]

Complete redesign of the lesson completion model. Currently, `markLessonComplete` is called from `handleNavComplete` — but Next never calls `onComplete` (only Finish does), so no lesson is ever reliably marked complete. Rather than patching the navigation flow, completion is decoupled from navigation entirely.

**New model:** each content block fires an independent completion event when sufficiently engaged with. `LessonView` tracks which blocks have fired. When all blocks have fired, the lesson is automatically marked complete in SQLite and the Next/Finish button activates. The user then clicks to navigate at their own pace.

**Block event contracts:**
- `TextBlock` → fires `textcomplete` after the block has been **continuously in the viewport for 1 second** (Intersection Observer + debounce timer). Clock starts on initial render if already visible.
- `VideoBlock` → fires `videocomplete` on YouTube IFrame Player API `ENDED` state (`YT.PlayerState.ENDED = 0`). Fallback: if the IFrame API fails to initialise within 5 s, uses Intersection Observer with a **3-second** threshold.
- `QuizBlock` wrapper → fires `quizcomplete` when `QuizCompleteEvent` fires and `score / maxScore >= passThreshold` (default `passThreshold = 0.0`). Failed attempts do not fire the event; quizazz handles retry internally.
- `ContentBlock.svelte` forwards each child event upward as a unified `blockcomplete` carrying the block index.

**Navigation cleanup:** `Navigation.svelte` handles its own routing — Next calls `navigateTo`, Finish calls `goto('/')`. `LessonView` no longer needs `handleNavComplete` or the `oncomplete` prop; it only passes a `disabled` flag to `Navigation`.

**Reactive progress store:** `$lib/stores/progress.ts` (new) exports a writable store holding `Record<string, ModuleProgress>` and an `invalidateProgress(curriculum)` helper that re-fetches all module progress from SQLite and writes to the store. `+layout.svelte` subscribes to this store instead of doing a one-shot fetch. Lesson completions call `invalidateProgress` so the sidebar updates immediately.

**Revisit behaviour:** On mount, `LessonView` reads the lesson's current DB status; if already `complete`, it pre-fills the completion set so Next/Finish is immediately active without requiring re-engagement.

**Zero-block edge case:** A lesson with no content blocks is treated as immediately complete on mount.

**Tasks:**

- [x] `sveltekit_template/src/lib/stores/progress.ts` (new):
  - [x] `progressStore`: writable `Record<string, ModuleProgress>`, initialised `{}`
  - [x] `invalidateProgress(curriculum: Curriculum | null): Promise<void>`: fetches all module progress and writes to store; no-op if `curriculum` is null
  - [x] Export both
- [x] `sveltekit_template/src/routes/+layout.svelte`:
  - [x] Replace the one-shot `$effect` progress fetch with a subscription to `progressStore`
  - [x] Call `invalidateProgress($curriculum)` when `$curriculum` becomes non-null
- [x] `sveltekit_template/src/lib/components/TextBlock.svelte`:
  - [x] On mount, create `IntersectionObserver`; when block enters viewport start a 1-second timer; cancel timer if block leaves viewport before 1 s; when timer fires, dispatch `textcomplete` (once only — guard against double-fire)
  - [x] Clean up observer and timer on component destroy
- [x] `sveltekit_template/src/lib/components/VideoBlock.svelte`:
  - [x] Inject YouTube IFrame API script tag if `window.YT` is not already loaded; wait for `window.onYouTubeIframeAPIReady`
  - [x] Create `YT.Player` on the video container; register `onStateChange` callback; when `event.data === YT.PlayerState.ENDED` dispatch `videocomplete` (once only)
  - [x] Fallback: if IFrame API not ready within 5 s, attach Intersection Observer with 3-second threshold instead
  - [x] Clean up player and observer on destroy
- [x] `sveltekit_template/src/lib/components/ContentBlock.svelte`:
  - [x] Listen for `textcomplete`, `videocomplete`, `quizcomplete` from child components
  - [x] Forward each as a `blockcomplete` custom event with `detail: { blockIndex: number }` to the parent `LessonView`
  - [x] Pass `passThreshold` from quiz block content to the `<QuizBlock>` component
- [x] `sveltekit_template/src/lib/components/LessonView.svelte`:
  - [x] On mount: call `getLessonProgress(moduleId, lesson.id)`; if status is `complete`, set `allBlocksComplete = true` immediately; otherwise initialise `completedBlocks = new Set<number>()`
  - [x] Handle `blockcomplete` events from `ContentBlock`: add `blockIndex` to `completedBlocks`; when `completedBlocks.size === lesson.content_blocks.length`, call `markLessonComplete(moduleId, lesson.id)` then `invalidateProgress($curriculum)`
  - [x] Derive `lessonComplete`: `allBlocksComplete || completedBlocks.size === lesson.content_blocks.length`
  - [x] Handle zero-block case: `lessonComplete = true` on mount if `lesson.content_blocks.length === 0`
  - [x] Pass `disabled={!lessonComplete}` to `<Navigation>`
  - [x] Remove `handleNavComplete` and `oncomplete` prop (no longer needed)
- [x] `sveltekit_template/src/lib/components/Navigation.svelte`:
  - [x] Accept `disabled: boolean` prop (default `false`)
  - [x] Apply `disabled` attribute and `opacity-50 cursor-not-allowed` style to Next/Finish button when `disabled`
  - [x] `goNext()`: if `next` → `navigateTo(next.moduleId, next.lessonId)`; else → `goto('/')` (import `goto` from `$app/navigation`)
  - [x] Remove `onComplete` prop — Finish now routes directly
- [x] `sveltekit_template/src/lib/types/index.ts`:
  - [x] `QuizContent` interface gains `passThreshold?: number`
- [x] Tests (vitest):
  - [x] `TextBlock.test.ts`: fires `textcomplete` after 1 s in viewport; does NOT fire if block leaves before 1 s; fires on first qualifying viewport interval only (no double-fire)
  - [x] `VideoBlock.test.ts`: mock `YT` global; ENDED state fires `videocomplete`; fallback: viewport 3 s fires `videocomplete` when YT API absent
  - [x] `LessonView.test.ts`: all blocks complete → `markLessonComplete` called and `invalidateProgress` called; button disabled until all blocks done; pre-fills set when lesson is already `complete`; zero-block lesson is immediately complete
  - [x] `progress.store.test.ts`: `invalidateProgress` writes fetched data to store; subsequent calls overwrite not append
- [x] Mirror all changes to `src/learningfoundry/sveltekit_template/`
- [x] Bump version to v0.42.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`
- [x] `CHANGELOG.md` — v0.42.0 under "Added" (block completion events, lesson auto-complete, reactive progress store) and "Changed" (Next/Finish no longer trigger completion marking)
- [x] Verify: `pyve test`, `pyve test tests/test_smoke_sveltekit.py`, `ruff`, `mypy`

**Out of scope:**
- Non-YouTube video providers (IFrame API is YouTube-specific; other providers use the viewport fallback until their own story)
- Per-lesson scroll memory on revisit

---

### Story I.h: v0.43.0 — Dashboard Curriculum Progress Bar [Done]

The dashboard (`/`) displays per-module progress bars but no curriculum-level summary. Add a single bar above the module cards showing overall completion. Depends on the reactive `progressStore` introduced in I.g.

**Display:**
```
12 of 40 lessons completed
[████████░░░░░░░░░░░░░░░░]
```

Computed from the reactive store as `sum(complete lessons across all modules) / sum(all lessons across all modules)`. Updates live when lessons complete during the session — no page reload required.

**Tasks:**

- [x] `sveltekit_template/src/lib/components/ProgressDashboard.svelte`:
  - [x] Compute `totalLessons = modules.reduce((n, m) => n + m.lessons.length, 0)`
  - [x] Compute `totalComplete = modules.reduce((n, m) => n + completeLessonCount(m, progress), 0)` where `completeLessonCount` counts lessons with status `complete`
  - [x] Render a `<ProgressBar percent={...}>` with label `"{totalComplete} of {totalLessons} lessons completed"` above the existing module card list
  - [x] Handle `totalLessons === 0` gracefully (no division by zero; hide bar or show 0%)
- [x] `sveltekit_template/src/routes/+page.svelte` (dashboard route):
  - [x] Confirm it passes `modules` and the reactive `progress` from `progressStore` to `ProgressDashboard` (wire if missing)
- [x] Tests (vitest):
  - [x] `ProgressDashboard.test.ts`: bar shows 0% when no lessons complete; bar shows 50% when half complete; bar shows 100% when all complete; label text is correct
- [x] Mirror changes to `src/learningfoundry/sveltekit_template/`
- [x] Bump version to v0.43.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`
- [x] `CHANGELOG.md` — v0.43.0 under "Added"
- [x] Verify: `pyve test`, smoke, `ruff`, `mypy`

**Out of scope:**
- Curriculum completion celebration / "Course Complete" screen (future story)
- Cross-module progress export

---

### Story I.i: v0.44.0 — Locking Configuration Schema [Done]

Python-side schema, resolver, config, and data pipeline changes for the content locking/unlocking system. Frontend locking UI is Story I.j and depends on this story's `curriculum.json` output.

**New YAML fields:**

```yaml
# curriculum.yml — top-level locking config (optional; inherits from global config if absent)
locking:
  sequential: true          # module N+1 requires module N complete; default false
  lesson_sequential: false  # lesson N+1 requires lesson N complete within a module; default false

modules:
  - id: mod-01
    locked: false           # per-module override; null/absent = inherit from curriculum/global
    lessons:
      - id: lesson-01
        unlock_module_on_complete: true  # when this lesson completes, unlocks siblings + next module
        content_blocks:
          - type: quiz
            source: quizazz
            ref: assessments/quiz.yml
            pass_threshold: 0.7         # optional float 0.0–1.0; default 0.0 (any completion)
```

**Config hierarchy (most local wins):**
1. Per-module `locked: bool` — direct boolean override, trumps everything
2. Curriculum `locking.sequential` — applies to modules without explicit `locked:`
3. Global `~/.config/learningfoundry/config.yml` `locking.sequential` — project-wide default

**Tasks:**

- [x] `src/learningfoundry/schema_v1.py`:
  - [x] New `LockingConfig` Pydantic model: `sequential: bool = False`, `lesson_sequential: bool = False`
  - [x] `CurriculumSchema` gains `locking: LockingConfig = Field(default_factory=LockingConfig)`
  - [x] `ModuleSchema` gains `locked: Optional[bool] = None` (None = inherit)
  - [x] `LessonSchema` gains `unlock_module_on_complete: bool = False`
  - [x] `QuizBlock` gains `pass_threshold: float = Field(0.0, ge=0.0, le=1.0)`
- [x] `src/learningfoundry/resolver.py`:
  - [x] `ResolvedCurriculum` carries `locking: LockingConfig`
  - [x] `ResolvedModule` carries `locked: Optional[bool]`
  - [x] `ResolvedLesson` carries `unlock_module_on_complete: bool`
  - [x] Resolved quiz content dict includes `pass_threshold` key
- [x] `src/learningfoundry/generator.py`:
  - [x] `curriculum.json` output includes top-level `locking` object, per-module `locked`, per-lesson `unlock_module_on_complete`, and per-quiz content `pass_threshold`
- [x] Global config (`config.py` or equivalent):
  - [x] Add `locking: LockingConfig` block to global config schema with defaults `sequential=False, lesson_sequential=False`
  - [x] Merge order: global config → curriculum YAML `locking`; per-module `locked` is a separate direct override, not part of the `LockingConfig` merge
- [x] `tests/test_schema_v1.py`:
  - [x] `LockingConfig` defaults: both fields False
  - [x] `pass_threshold` validates 0.0–1.0; rejects values outside range
  - [x] `unlock_module_on_complete` defaults False; round-trips True
  - [x] `locked: null` (absent), `locked: false`, `locked: true` all parse correctly
  - [x] Full curriculum with locking fields round-trips through parse → serialize
- [x] `tests/test_resolver.py`:
  - [x] Locking fields appear in resolved curriculum output
  - [x] Quiz `pass_threshold` propagated into content dict
  - [x] `unlock_module_on_complete` propagated onto resolved lesson
- [x] `tests/test_smoke_sveltekit.py`:
  - [x] `curriculum.json` includes `locking`, `locked`, `unlock_module_on_complete`, `pass_threshold`
- [x] `tests/fixtures/valid-curriculum.yml`:
  - [x] Add top-level `locking:` block and one lesson with `unlock_module_on_complete: true` and one quiz block with `pass_threshold: 0.5`
- [x] `docs/specs/features.md`:
  - [x] FR-1 (YAML Parsing): document `LockingConfig`, `locked`, `unlock_module_on_complete`, `pass_threshold`
  - [x] FR-4 (Progress Tracking): add sub-section on locking config and how sequential access is enforced
- [x] `docs/specs/tech-spec.md`:
  - [x] Schema section: `LockingConfig` model, new fields on `CurriculumSchema`, `ModuleSchema`, `LessonSchema`, `QuizBlock`
  - [x] Data Models section: `ResolvedCurriculum.locking`, `ResolvedModule.locked`, `ResolvedLesson.unlock_module_on_complete`
- [x] `README.md` — new "Content locking" subsection under Curriculum YAML Format documenting the three-level hierarchy and `unlock_module_on_complete`
- [x] Bump version to v0.44.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`
- [x] `CHANGELOG.md` — v0.44.0 under "Added"
- [x] Verify: `pyve test`, smoke, `ruff`, `mypy`

**Out of scope:**
- Frontend locking UI (Story I.j)
- Reset button

---

### Story I.j: v0.45.0 — Locking and Unlocking UI [Done]

Frontend implementation of the locking/unlocking system. Depends on I.i (schema + `curriculum.json` locking fields) and I.g (reactive progress store + block completion model).

**Locked module:** Cannot be expanded; lesson list is never rendered; card shows a Lucide `Lock` icon; header click is a no-op.

**Locked lesson:** Non-interactive row in the lesson list — `cursor-not-allowed`, muted text, no click handler. No lock icon needed; the visual muting is sufficient in context.

**`unlock_module_on_complete` cascade** (fires inside `LessonView` when all blocks complete and `lesson.unlockModuleOnComplete` is true):
1. All other lessons in the same module become **optional** — accessible but not required for module completion.
2. The immediately following module in the curriculum sequence is unlocked — it becomes expandable and navigable regardless of sequential locking state.

Optional state is **derived at render time** from curriculum config + progress store — no new DB table is required. The key question: is the key lesson (`unlockModuleOnComplete: true`) in this module already `complete` in the progress store? If yes → siblings are optional; if no → siblings are locked (when sequential mode is on).

**Optional lesson indicator:** `◇` (neutral diamond), styled `text-gray-400`. Distinct from `○` (not started / `text-gray-300`), `…` (in progress / `text-blue-500`), `✓` (complete / `text-green-600`).

**Module completion with optional lessons:** A module is `complete` when all non-optional lessons are `complete`. Optional lessons that happen to be completed still count toward the curriculum-level progress bar in `ProgressDashboard`.

**Tasks:**

- [x] `sveltekit_template/src/lib/types/index.ts`:
  - [x] `LessonStatus` gains `'optional'`
  - [x] `Lesson` interface gains `unlockModuleOnComplete?: boolean`
  - [x] `Module` interface gains `locked?: boolean`
  - [x] `Curriculum` interface gains `locking?: LockingConfig`
  - [x] New `LockingConfig` TypeScript interface: `{ sequential: boolean; lessonSequential: boolean }`
- [x] `sveltekit_template/src/lib/utils/locking.ts` (new):
  - [x] `resolveLocking(curriculum, globalLocking)`: returns effective `LockingConfig` (curriculum overrides global; per-module `locked` is a separate pass)
  - [x] `isModuleLocked(moduleIndex, curriculum, progress, globalLocking): boolean`: locked if (a) explicit `module.locked === true`, or (b) sequential mode + previous module not complete; first module is never locked by sequential rule alone
  - [x] `isLessonLocked(moduleId, lessonIndex, curriculum, progress, globalLocking): boolean`: locked if lesson_sequential mode and previous lesson in same module not complete
  - [x] `getOptionalLessons(moduleId, curriculum, progress): Set<string>`: returns IDs of sibling lessons that are optional (key lesson for this module is `complete` in progress)
  - [x] `isModuleComplete(moduleId, curriculum, progress): boolean`: all non-optional lessons are `complete` (uses `getOptionalLessons` to exclude optional lessons from the requirement)
- [x] `sveltekit_template/src/routes/+layout.svelte`:
  - [x] Import `isModuleLocked`, `isLessonLocked`, `getOptionalLessons` from `$lib/utils/locking.ts`
  - [x] Derive per-module locked state and per-lesson locked/optional state from `$curriculum`, `$progressStore`, and global config
  - [x] Pass derived locked/optional state to `<ModuleList>`
- [x] `sveltekit_template/src/lib/components/ModuleList.svelte`:
  - [x] Accept `lockedModules: Set<string>` prop
  - [x] Locked module card: `onclick` is no-op; `aria-disabled="true"`; show `<Lock size={14}>` (Lucide) next to module title; do not render `<LessonList>` or `<ProgressBar>` expand panel
  - [x] Do not apply active-module highlight to a locked module
- [x] `sveltekit_template/src/lib/components/LessonList.svelte`:
  - [x] Accept `optionalLessons: Set<string>` and `lockedLessons: Set<string>` props (both default `new Set()`)
  - [x] Locked lesson: `cursor-not-allowed text-gray-300`; click handler is no-op
  - [x] Optional lesson: `statusIcon` returns `◇`; `statusClass` returns `text-gray-400`
  - [x] Update `statusIcon` and `statusClass` to handle `optional` status (from progress store) and locked override (from `lockedLessons` prop)
- [x] `sveltekit_template/src/lib/components/LessonView.svelte`:
  - [x] After `markLessonComplete` and `invalidateProgress`, check `lesson.unlockModuleOnComplete`; if true, call `invalidateProgress($curriculum)` again (the progress store re-derive will pick up the new `complete` status and `getOptionalLessons` / `isModuleLocked` will return the updated state automatically — no extra DB write needed)
- [x] `sveltekit_template/src/lib/components/ProgressDashboard.svelte`:
  - [x] Accept `optionalLessons` per module; use `isModuleComplete` for per-module status badge (excludes optional lessons from requirement)
  - [x] Curriculum-level bar: continue counting all completed lessons (optional or not) toward `totalComplete`
- [x] Tests (vitest):
  - [x] `locking.test.ts`:
    - [x] `isModuleLocked`: first module never locked; second module locked when sequential + first module incomplete; unlocked when first module complete; `locked: false` override beats sequential rule; `locked: true` override forces locked even when previous complete
    - [x] `isLessonLocked`: lesson 2 locked when `lessonSequential` + lesson 1 incomplete; unlocked when lesson 1 complete
    - [x] `getOptionalLessons`: returns empty set before key lesson complete; returns all sibling IDs after key lesson complete
    - [x] `isModuleComplete`: false while non-optional lessons incomplete; true when all non-optional done; optional lessons do not block completion
  - [x] `ModuleList.test.ts`: locked module header click is no-op; lock icon rendered; lesson list not rendered for locked module
  - [x] `LessonList.test.ts`: locked lesson click is no-op; optional lesson shows `◇`; complete lesson shows `✓`
- [x] Mirror all changes to `src/learningfoundry/sveltekit_template/`
- [x] Bump version to v0.45.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`
- [x] `CHANGELOG.md` — v0.45.0 under "Added"
- [x] Verify: `pyve test`, smoke, `ruff`, `mypy`

**Out of scope:**
- Reset button (course / module / lesson)
- Tooltip/explanation when learner clicks a locked lesson
- Animated unlock transition
- Lesson-level `locked: bool` override (module-level and sequential rules cover v1 cases)

---

### Story I.k: v0.46.0 — Lesson Navigation Lifecycle Fix and E2E Harness [Done]

Three user-visible regressions reproduced consistently against any multi-lesson curriculum after v0.45.0: (1) progress is never recorded — no sidebar checkmarks, no module %, no curriculum progress bar movement; (2) Next/Finish is deactivated when revisiting a previously completed lesson, contrary to FR-P2; (3) the old video block remains visible when navigating between two lessons that both contain a `video` block.

All three trace to a single navigation defect introduced in I.g and missed by the I.f/I.g vitest harness because that harness mocks `$app/navigation`. Story I.g specified `Navigation.goNext()` calls `navigateTo(next.moduleId, next.lessonId)`, but `navigateTo` (`stores/curriculum.ts`) is the curriculum-store helper — it sets `currentPosition` and nothing else. The lesson route reads from `page.params`, not from `currentPosition`. So in-app navigation updates the sidebar highlight but never the URL; `LessonView` is never re-mounted; `markLessonInProgress` runs only for the first lesson reached by direct URL; `allBlocksComplete` and `completedBlocks` go sticky across "navigations"; and the index-keyed `{#each lesson.content_blocks as block, i (i)}` inside the reused `LessonView` reuses the same `<VideoBlock>` instance for the new lesson's video. See `phase-I-progress-ux-subplan.md` → "Discovered Post-Shipping" → FR-P9, FR-P10, FR-P11 for the full analysis.

**Tasks:**

- [x] FR-P9: lesson navigation actually changes the URL.
  - [x] `sveltekit_template/src/lib/components/Navigation.svelte`: `goNext()` calls `goto(\`/${next.moduleId}/${next.lessonId}\`)` when `next` exists, else `goto('/')`. `goPrev()` calls `goto(\`/${prev.moduleId}/${prev.lessonId}\`)`. Remove the `navigateTo` import.
  - [x] `sveltekit_template/src/lib/components/LessonList.svelte`: `handleClick(lessonId)` calls `goto(\`/${moduleId}/${lessonId}\`)` (after the `resolveLessonClick` lock check) instead of `navigateTo(moduleId, lessonId)`. Remove the `navigateTo` import.
  - [x] `sveltekit_template/src/lib/components/ProgressDashboard.svelte`: `resumeFirst(mod)` calls `goto(\`/${mod.id}/${target.id}\`)` instead of `navigateTo`.
  - [x] `sveltekit_template/src/lib/stores/curriculum.ts`: keep `navigateTo` callable for the route's URL→store sync (`[module]/[lesson]/+page.svelte`'s `$effect`), but add a JSDoc comment marking it as **internal route-sync only — UI code must use `goto`**. Optionally rename to `setPositionFromRoute` to remove the foot-gun name (decide during implementation).
- [x] FR-P10: component lifecycle invariants.
  - [x] `sveltekit_template/src/routes/[module]/[lesson]/+page.svelte`: wrap `<LessonView … />` in `{#key \`${currentModule.id}/${currentLesson.id}\`} … {/key}` so `LessonView` (and the route-internal subtree) is guaranteed to tear down and re-mount when either route param changes, even if SvelteKit would otherwise reuse the page component.
  - [x] `sveltekit_template/src/lib/components/LessonView.svelte`: replace `{#each lesson.content_blocks as block, i (i)}` with a stable identity key — first non-null of `block.ref`, `(block.content as any).url` for video, otherwise `\`${block.type}-${i}\``. Document the choice in a one-line comment.
  - [x] `sveltekit_template/src/lib/components/VideoBlock.svelte`: in addition to `onMount`, add an `$effect` watching `content.url`. When the URL changes, call `player?.destroy?.()`, clear `fired`, and re-create the player with the new `videoId`. Same fallback path applies if the player creation fails. Cleanup on destroy still runs both the player and observer cleanup.
- [x] FR-P11: end-to-end test harness.
  - [x] `sveltekit_template/package.json`: add `@playwright/test` dev dependency and `"e2e": "playwright test"` script. Postinstall step or README note: `pnpm exec playwright install chromium`.
  - [x] `sveltekit_template/playwright.config.ts`: configure to run against `pnpm preview` (built static site) on a dynamic port; single project (chromium); `e2e/` test dir.
  - [x] `sveltekit_template/e2e/` (new):
    - [x] `e2e/fixtures/curriculum.json` — minimal 2-module / 4-lesson fixture with one video block in each of two consecutive lessons; one fast-completing text block per lesson (or use the existing static curriculum if a fixture isn't viable). YouTube fixtures should use a known short test video.
    - [x] `e2e/navigation.spec.ts`:
      - [x] Sidebar lesson click: clicks lesson 2; URL is `/mod-01/lesson-02`; lesson 2 title is rendered.
      - [x] Next button: complete lesson 1 (force-fire blockcomplete via test hook or wait for the 1 s text intersection timer); click Next; URL advances to lesson 2; lesson 2 title is rendered.
      - [x] Returning to a completed lesson: complete lesson 1, click Next, click lesson 1 in sidebar; Next button is enabled immediately (not disabled).
    - [x] `e2e/progress.spec.ts`:
      - [x] Complete lesson 1; assert sidebar lesson row gains `✓` indicator without page reload.
      - [x] Complete all lessons in module 1; assert module 1's % reaches 100 in the sidebar and dashboard without reload.
      - [x] Assert curriculum-level bar text updates from `0 of N` to `1 of N` after the first lesson completes.
    - [x] `e2e/video.spec.ts`:
      - [x] Open lesson with video A; assert exactly one YouTube iframe in the DOM with the expected `videoId`.
      - [x] Navigate to lesson with video B; assert exactly one iframe, with B's `videoId` (not A's). Old iframe is destroyed.
  - [x] `tests/test_smoke_sveltekit.py`: extend the smoke pipeline so `pnpm e2e` runs after `pnpm build` against the smoke-built site. The Playwright fixture curriculum is built by the same generator code path. Skip the e2e leg gracefully if `playwright` browsers aren't installed locally (CI installs them in setup).
- [x] Vitest gap-fill (smaller, faster regression coverage):
  - [x] `Navigation.test.ts`: `goNext` calls `goto` with the expected path string (not `navigateTo`); `goNext` calls `goto('/')` when `next === null`; disabled state suppresses both.
  - [x] `LessonList.test.ts`: clicking a non-locked lesson row calls `goto` with `\`/${moduleId}/${lessonId}\``; clicking a locked row is a no-op.
  - [x] `VideoBlock.test.ts`: changing `content.url` while the component stays mounted destroys the previous player and creates a new one with the new `videoId`; `fired` is reset.
- [x] Mirror all `sveltekit_template/` changes to `src/learningfoundry/sveltekit_template/`.
- [x] Bump version to v0.46.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] `CHANGELOG.md` — v0.46.0 under "Fixed" (lesson navigation routing, sticky LessonView state, stale video block) and "Added" (Playwright e2e harness; vitest navigation regression coverage).
- [x] Verify: `pyve test`, `pyve test tests/test_smoke_sveltekit.py`, `pnpm test`, `pnpm e2e`, `ruff`, `mypy`.

**Out of scope:**
- Per-lesson scroll memory on revisit (still deferred from I.b).
- Generalising the `{#key}` lifecycle pattern to other routes that don't currently need it.
- Replacing `navigateTo` everywhere with `goto`: the curriculum store still syncs from route params via the existing `$effect` in `[module]/[lesson]/+page.svelte`; that internal call site is intentional.
- Cross-tab progress sync, progress export/import, and other items already listed under Future.

---

### Story I.l: v0.47.0 — Reset Course Button [Done]

The subplan's "Deferred (documented, not implemented)" list has long included a course/module/lesson reset capability. Course-level reset is now **promoted to active scope** because (a) it is genuinely learner-facing — "I want to retake this course from scratch" — and (b) it is a much better dev/QA affordance than DevTools-level IndexedDB clearing for verifying I.k, I.m, and I.n fixes interactively. Per-module and per-lesson reset remain Deferred (independently useful but distinct UX problems). See `phase-I-progress-ux-subplan.md` → FR-P12.

The button is pinned at the bottom of the sidebar `<aside>`, disabled when no learner activity exists for this curriculum and enabled as soon as any of `lesson_progress`, `quiz_scores`, `exercise_status` contains a row. Clicking it opens a confirmation dialog; on confirm, all three progress tables are truncated, the curriculum store position and any expanded sidebar module are cleared, and the learner is sent to `/`.

**Tasks:**

- [x] `sveltekit_template/src/lib/db/progress.ts`:
  - [x] New `resetProgress(): Promise<void>` — `DELETE FROM lesson_progress; DELETE FROM quiz_scores; DELETE FROM exercise_status` then `persistDb()`. Single DB transaction.
- [x] `sveltekit_template/src/lib/utils/progress.ts` (new):
  - [x] Pure function `hasAnyProgress(store: Record<string, ModuleProgress>): boolean` — true if any module has any lesson with status other than `not_started`. Quiz scores and exercise statuses are reflected in `lesson_progress` via `markLessonInProgress`/`markLessonComplete` cascades; if a future feature lets either advance independently of lesson state, extend this helper to read from those tables directly.
- [x] `sveltekit_template/src/lib/components/ResetCourseButton.svelte` (new):
  - [x] Props: `disabled: boolean`.
  - [x] Disabled state styling: `text-gray-300 cursor-not-allowed`.
  - [x] Enabled state styling: `text-red-600 hover:bg-red-50` (muted destructive).
  - [x] On click (enabled only): show a confirmation. First cut may use `window.confirm("Reset all progress for this curriculum? This cannot be undone.")`; flag a follow-up for a styled `<dialog>` modal once basic plumbing is verified.
  - [x] On confirm: `await resetProgress(); currentPosition.set(null); await invalidateProgress($curriculum); await goto('/');` (the `currentPosition.set(null)` triggers the FR-P14 sidebar collapse path if Story I.n has shipped — this story should not depend on I.n landing first; it just sets the store and lets I.n's effect take over when present).
- [x] `sveltekit_template/src/routes/+layout.svelte`:
  - [x] Convert the `<aside>` to a flex column (`flex flex-col`) so the existing scrollable module list and the new reset button can share the column without the button scrolling away.
  - [x] Render `<ResetCourseButton disabled={!hasAnyProgress($progressStore)} />` at the bottom of the `<aside>` with `mt-auto` (or a separate `<footer>` block inside the aside) so it pins to the bottom even when the module list is short.
- [x] Tests (vitest):
  - [x] `progress.utils.test.ts`: `hasAnyProgress` returns false for `{}`; false when every lesson status is `not_started`; true with one `in_progress` lesson; true with one `complete` lesson; true with one `optional` lesson that has been touched.
  - [x] `db.progress.test.ts`: extend with a `resetProgress` case — pre-seed all three tables, run reset, then assert each `getX` returns null/empty.
  - [x] `ResetCourseButton.test.ts`: `disabled` prop suppresses click handler; enabled click invokes confirm and calls `resetProgress` only when confirm returns true; cancelled confirm does not call `resetProgress` and does not navigate.
- [x] Playwright e2e (extends I.k harness):
  - [x] `e2e/reset.spec.ts`: load curriculum → button is disabled → complete one text block (wait for the 1 s sentinel after Story I.m, or use a short block before I.m) → button enables → click reset → confirm dialog → on confirm, assert sidebar checkmark gone, module % returns to 0, dashboard text reads "0 of N completed", URL is `/`.
- [x] Mirror all `sveltekit_template/` changes to `src/learningfoundry/sveltekit_template/`.
- [x] `docs/specs/features.md` — under FR-4 (Progress Tracking), document the reset capability and that it is course-scoped (not per-module/lesson in v1).
- [x] `docs/specs/tech-spec.md` — document the new `resetProgress` DB op and the `ResetCourseButton` component briefly.
- [x] `README.md` — short note under a "Resetting progress" subsection or under Curriculum YAML / runtime behaviour.
- [x] Bump version to v0.47.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] `CHANGELOG.md` — v0.47.0 under "Added" (Reset course button + reactive activation).
- [x] Verify: `pyve test`, `pyve test tests/test_smoke_sveltekit.py`, `pnpm test`, `pnpm e2e`, `ruff`, `mypy`.

**Out of scope:**
- Per-module reset and per-lesson reset (still Deferred).
- Resetting an individual quiz score or exercise status without resetting its parent lesson.
- Undo for reset (the action is destructive by design; the confirmation dialog is the safety net).
- Cross-tab synchronisation of reset (other tabs viewing the curriculum won't update until they re-fetch progress).
- Server-side / cloud-backed progress reset.

---

### Story I.m: v0.48.0 — Text Block End-of-Block Completion [Done]

FR-P1's text-block trigger fires whenever any portion of the block is in the viewport for 1 s. For a long lesson with one tall text block, simply landing on the page satisfies the trigger because the top of the block is always in view — the learner gets a completion event without ever scrolling to the actual lesson body. Refined trigger: a sentinel placed at the **end** of the rendered markdown must be continuously visible for 1 s. See `phase-I-progress-ux-subplan.md` → FR-P13.

**Tasks:**

- [x] `sveltekit_template/src/lib/components/TextBlock.svelte`:
  - [x] Render a sentinel `<div bind:this={sentinelEl} aria-hidden="true" data-textblock-end></div>` immediately after the `{@html html}` rendering. Zero-size by default (no padding/margin); browsers treat it as observable for `IntersectionObserver` regardless.
  - [x] Switch the `IntersectionObserver` target from `blockEl` to `sentinelEl`. Keep `blockEl` bound for any future work that needs the wrapper (e.g. FR-P10 `$effect`-driven content swaps if a non-route-driven flow ever needs it), but rename it to `wrapperEl` if the binding is no longer functionally used to make the role explicit.
  - [x] Threshold remains `0.1`; debounce remains 1 s; single-fire `fired` guard unchanged.
- [x] Tests (vitest):
  - [x] `TextBlock.test.ts` — short block (sentinel in viewport at mount) fires `textcomplete` after 1 s. Regression check; matches old behaviour.
  - [x] `TextBlock.test.ts` — tall block, sentinel never intersects: simulate observer entries with `isIntersecting: false` for the sentinel; assert `textcomplete` does NOT fire after 1 s, 2 s, or 5 s.
  - [x] `TextBlock.test.ts` — tall block, sentinel becomes visible after a simulated scroll: dispatch a `isIntersecting: true` entry for the sentinel; assert `textcomplete` fires 1 s later.
  - [x] `TextBlock.test.ts` — sentinel briefly visible for less than 1 s (e.g. 700 ms then `isIntersecting: false`): assert `textcomplete` does not fire.
- [x] Playwright e2e (extends I.k harness):
  - [x] `e2e/text-block-bottom.spec.ts`: load a curriculum with one tall text block (height > viewport height); wait 5 s without scrolling; assert no sidebar checkmark and module % is 0. Scroll to the bottom of `<main>`; assert checkmark appears within 2 s of the sentinel becoming visible.
- [x] `docs/specs/features.md` — update FR-1's text-block completion description to reference end-of-block trigger and link to the rationale (or leave inline if compact).
- [x] `docs/specs/tech-spec.md` — update `TextBlock` description to mention the sentinel pattern.
- [x] Mirror all `sveltekit_template/` changes to `src/learningfoundry/sveltekit_template/`.
- [x] Bump version to v0.48.0.
- [x] `CHANGELOG.md` — v0.48.0 under "Changed" (text-block completion now requires the bottom of the block to be in view, not just any portion).
- [x] Verify: `pyve test`, `pyve test tests/test_smoke_sveltekit.py`, `pnpm test`, `pnpm e2e`, `ruff`, `mypy`.

**Out of scope:**
- Per-paragraph engagement tracking or scroll-percentage-based completion.
- Reading-time estimation as an alternative completion signal.
- Configurable per-block completion criteria (would need a curriculum YAML schema change).
- Backporting the sentinel pattern to `VideoBlock`'s viewport fallback — that fallback only fires when the IFrame API itself is unavailable, an uncommon enough path that it doesn't justify the same refinement. Revisit if the fallback ever becomes the primary path.

---

### Story I.n: v0.49.0 — Clean Dashboard State on Finish [Done]

After I.k, clicking Finish on the last lesson sends the learner to `/` correctly, but the sidebar still shows the last module expanded with the last lesson highlighted. The learner just declared "I'm done" and the UI keeps marking that lesson as their current focus — jarring. Refined behaviour: Finish clears the active-lesson highlight and collapses the previously expanded module. See `phase-I-progress-ux-subplan.md` → FR-P14.

**Tasks:**

- [x] `sveltekit_template/src/lib/components/Navigation.svelte`:
  - [x] In `goNext()`, the `next === null` branch becomes `currentPosition.set(null); void goto('/');` — the position clear runs first so the auto-expand effect in `ModuleList` reacts before the route change settles. Import `currentPosition` from `$lib/stores/curriculum.js`.
- [x] `sveltekit_template/src/lib/components/ModuleList.svelte`:
  - [x] Extend the existing auto-expand `$effect`: when `pos === null`, set `expandedModuleId = null` and `lastAutoExpandedModuleId = null`. The existing manual-toggle preservation logic (`pos.moduleId !== lastAutoExpandedModuleId`) is unchanged for the non-null case.
- [x] Tests (vitest):
  - [x] `Navigation.test.ts` — extend the I.k regression suite: `goNext` on a lesson with `next === null` calls `currentPosition.set(null)` and `goto('/')` (verify call order via mock).
  - [x] `ModuleList.test.ts` — when `currentPosition` transitions from `{moduleId: 'mod-01', lessonId: 'lesson-01'}` to `null`, both `expandedModuleId` and `lastAutoExpandedModuleId` reset to `null`. After the reset, a manual toggle still works (a regression check that the I.f fix is still intact).
- [x] Playwright e2e (extends I.k harness):
  - [x] `e2e/finish.spec.ts`: navigate to the last lesson, complete it, click Finish; assert URL is `/`, no sidebar `LessonList` row carries the active highlight (`bg-blue-100`), no module is expanded (no visible lesson list panel), and the curriculum-title link still works (clicking it does nothing visible since we're already at `/`, but doesn't error).
- [x] Mirror all `sveltekit_template/` changes to `src/learningfoundry/sveltekit_template/`.
- [x] Bump version to v0.49.0.
- [x] `CHANGELOG.md` — v0.49.0 under "Changed" (Finish on the last lesson now clears the active-lesson highlight and collapses the previously expanded sidebar module).
- [x] Verify: `pyve test`, `pyve test tests/test_smoke_sveltekit.py`, `pnpm test`, `pnpm e2e`, `ruff`, `mypy`.

**Out of scope:**
- Clearing sidebar state on navigations to `/` from sources other than Finish (e.g. clicking the curriculum-title link, browser back button).
- A dedicated "Course complete" celebration screen — see Future.
- Animated module collapse / lesson de-highlight transitions.

---

### Story I.o: v0.50.0 — Restore Text-Block Completion and Harden E2E Coverage [Done]

After v0.49.0 shipped, lesson completion stopped firing and recording entirely against real curricula: no sidebar checkmarks, no module % advancement, no curriculum-bar movement, and lesson revisits looked indistinguishable from first visits. Bisecting localised the regression to **v0.48.0 (Story I.m)**, masked by I.n shipping immediately after.

`TextBlock.svelte`'s I.m sentinel — `<div bind:this={sentinelEl} aria-hidden="true" data-textblock-end></div>` — has zero area (no content, no `min-height`, default block-level `height: 0`). The `IntersectionObserver` retained FR-P1's `threshold: 0.1`. With a zero-area target, `intersectionRatio = intersectionArea / targetArea` degenerates and never crosses 0.1; in real browsers, the observer's `isIntersecting: true` branch never fires. `textcomplete` is never emitted, `markLessonComplete` is never called, no row hits `lesson_progress`, and the on-revisit `getLessonProgress` returns `not_started`. See `phase-I-progress-ux-subplan.md` → "Addendum: Regression Discovered After v0.49.0".

The fix itself is one line. The bulk of the story is closing the three test gaps that let the regression reach `[Done]` and then ship through I.n undetected — the I.k–I.n harness asserted the cheapest checkable surface near each change rather than the user-visible outcome (vitest tested a `createViewportTracker` helper without ever instantiating a real `IntersectionObserver`; `e2e/text-block-bottom.spec.ts` was watered down to a sentinel-element-attached check; `e2e/progress.spec.ts` stops at `not_started → in_progress` rather than `→ complete` as FR-P11 specified).

**Tasks:**

- [x] Fix the sentinel — `sveltekit_template/src/lib/components/TextBlock.svelte`:
  - [x] Give the sentinel observable area: `<div bind:this={sentinelEl} aria-hidden="true" data-textblock-end style="height: 1px;"></div>`. 1 px is invisible to the learner and large enough for `IntersectionObserver` to compute a non-degenerate `intersectionRatio` against the configured 0.1 threshold.
  - [x] Update the existing block comment to explain why a non-zero height is required (one short line: "1 px height keeps the observer firing — a zero-area target degenerates intersectionRatio to 0").
- [x] Vitest — exercise the real observer, not just the helper. `sveltekit_template/src/lib/components/TextBlock.test.ts` (extend, do not delete):
  - [x] Add `@testing-library/svelte` as a dev dependency if not already present.
  - [x] New test: mount `<TextBlock>` with `@testing-library/svelte`; capture the actual element passed to `IntersectionObserver.observe()` (stub the constructor to record the target). Assert the recorded target's `getBoundingClientRect()` reports a non-zero `height`. This catches the "sentinel is zero-area" class of bug at the unit-test layer.
  - [x] Keep the existing `createViewportTracker` callback tests — they remain useful for the timer/debounce logic; just no longer the only line of defence.
- [x] Playwright — add a real completion smoke test. `sveltekit_template/e2e/progress.spec.ts` (extend):
  - [x] New test: navigate to a short text-block lesson (sentinel in viewport at first render); wait at least 1.5 s for the completion timer to fire; assert the sidebar status icon for that lesson transitions from `…` to `✓` *without page reload*. Use `page.locator('aside nav ul ul button').first()` and a `toHaveText('✓')` assertion with a generous timeout.
  - [x] New test: complete lesson 1 as above, then click another lesson, then click back to lesson 1; assert the Next/Finish button is enabled immediately (revisit pre-fill working — FR-P2 / I.g revisit semantics).
  - [x] New test: complete lesson 1; assert the dashboard's overall "X of N completed" text increments by 1 — closes FR-P11's "module % advances" bullet.
- [x] Playwright — make the tall-block scroll case actually run. `sveltekit_template/e2e/text-block-bottom.spec.ts` (rewrite):
  - [x] Drop the "structural existence" check. Use a fixture (smoke or dedicated; see next task) with one text block taller than the viewport.
  - [x] Test 1: load the lesson; wait 5 s without scrolling; assert the sidebar status icon does NOT transition to `✓` (fail-closed semantics for tall blocks).
  - [x] Test 2: scroll `<main>` to the bottom (via `page.locator('main').evaluate(el => el.scrollTo(0, el.scrollHeight))`); assert the sidebar status icon becomes `✓` within 2 s of the sentinel reaching viewport.
- [x] Decouple e2e fixtures from content drift. `sveltekit_template/e2e/`:
  - [x] Add `e2e/fixtures/curriculum.json` — a small hand-authored or generated curriculum with: one short text-block lesson (for the progress completion test), one tall text-block lesson (for the bottom-of-block scroll test), and at least three lessons total so navigation sequences are exercisable.
  - [x] Update `playwright.config.ts` to serve `e2e/fixtures/curriculum.json` instead of the smoke-built one when running e2e (e.g. via a Vite alias, a static file copy in a `globalSetup` script, or a per-test `page.route('/curriculum.json', …)` interception).
  - [x] `e2e/README.md` (new): document the fixture and how to regenerate it from a YAML source if desired.
- [x] Mirror all `sveltekit_template/` changes to `src/learningfoundry/sveltekit_template/`.
- [x] Bump version to v0.50.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] `CHANGELOG.md` — v0.50.0 under "Fixed" (text-block completion regression introduced in v0.48.0; lessons no longer fail to mark complete, sidebar checkmarks reappear, revisits correctly pre-fill the Next button) and "Added" (real-DOM TextBlock vitest coverage; lesson-completion e2e tests covering FR-P11; tall-text-block scroll-to-complete e2e test; dedicated `e2e/fixtures/` curriculum decoupled from smoke fixture drift).
- [x] Verify: `pyve test`, `pyve test tests/test_smoke_sveltekit.py`, `pnpm test`, `pnpm e2e`, `ruff`, `mypy`.

**Out of scope:**
- Per-paragraph engagement tracking, scroll-percentage thresholds, reading-time estimation (still Out of Scope from FR-P13).
- Visual regression testing infrastructure (screenshot diffs).
- Network mocking / record-replay for e2e tests.
- Auditing every other component for the same zero-area-target trap. `VideoBlock`'s viewport fallback uses the wrapper element (non-zero size); other observers in the codebase, if any, are out of scope here and can be checked opportunistically when touched.
- Backporting the harness improvements to a CI pipeline configuration if one does not yet exist for the SvelteKit template — that's a separate infrastructure story.

---

### Story I.p: v0.51.0 — Lesson Lifecycle Events and 'opened' Status [Done]

The lesson lifecycle today persists three states — `not_started`, `in_progress`, `complete` — plus the orthogonal `optional`. "Opened" and "in_progress" are conflated: both are written at the same moment in `LessonView.onMount` by `markLessonInProgress`. As a result, a learner who opens a lesson but engages with no content blocks (broken pipeline, brief glance, the I.o regression class) is indistinguishable in the data from one genuinely partway through. Both look like `…` in the sidebar; both count as `in_progress` everywhere downstream. External listeners — analytics, telemetry, a future "stuck lessons" dashboard — cannot subscribe to a clean "lesson opened" signal without coupling to the FR-P2 status machine. See `phase-I-progress-ux-subplan.md` → FR-P15 for the full design.

This story splits the conflation along three dimensions: a status-enum extension (`opened`), three custom-event emitters from `LessonView` (`lessonopen`, `lessonengage`, `lessoncomplete`), and an explicit decision to keep the sidebar visual mapping unchanged so the new internal granularity does not multiply learner-visible symbols. A fourth event `lessonresume` is parked in the Future section.

**Tasks:**

- [x] `sveltekit_template/src/lib/types/index.ts`:
  - [x] `LessonStatus` adds `'opened'` between `'not_started'` and `'in_progress'`. Order in the literal union: `'not_started' | 'opened' | 'in_progress' | 'complete' | 'optional'`. (Type union order is cosmetic for TS but documents the lifecycle progression.)
- [x] `sveltekit_template/src/lib/db/progress.ts`:
  - [x] New `markLessonOpened(moduleId, lessonId): Promise<void>` — `INSERT INTO lesson_progress (module_id, lesson_id, status, completed_at) VALUES (?, ?, 'opened', NULL) ON CONFLICT(module_id, lesson_id) DO UPDATE SET status = CASE WHEN status IN ('opened', 'in_progress', 'complete') THEN status ELSE 'opened' END`. Upgrade-only — never demotes an existing in_progress/complete row.
  - [x] `markLessonInProgress` semantics narrow: now called only on the *first* block-completion of the mount session, not on mount. The function body unchanged (still `INSERT … status='in_progress' … ON CONFLICT … status = CASE WHEN status = 'complete' THEN 'complete' ELSE 'in_progress' END`). Update its block comment to reflect the new caller contract.
  - [x] `getLessonProgress` already returns the `status` field unchanged; verify the typed return value compiles against the extended `LessonStatus` union (the `as` cast at line 48 needs the new value in the literal type).
  - [x] `getModuleProgress`'s module-status derivation already uses `s !== 'not_started'` for the `in_progress` branch — the new `opened` value falls into that branch correctly. Add a one-line comment confirming this is intentional so a future refactorer doesn't trip on the condition.
- [x] `sveltekit_template/src/lib/components/LessonView.svelte`:
  - [x] `onMount`: call `markLessonOpened(moduleId, lesson.id)` *before* the existing `getLessonProgress` revisit check. Dispatch a `lessonopen` custom event with `detail: { moduleId, lessonId: lesson.id }`. The existing zero-block edge case still calls `markLessonComplete` directly — but now it should also dispatch `lessonopen` *and* `lessoncomplete` in order before returning, so the event contract matches the data contract for instant-complete lessons.
  - [x] Track engagement state with a new `let engaged = $state(false)`. In `handleBlockComplete`, before adding to `completedBlocks`, if `!engaged` and the lesson is not already complete, set `engaged = true`, call `markLessonInProgress(moduleId, lesson.id)`, and dispatch `lessonengage` with `detail: { moduleId, lessonId: lesson.id }`.
  - [x] When `completedBlocks.size === lesson.content_blocks.length`, after `markLessonComplete` and `invalidateProgress` succeed, dispatch `lessoncomplete` with `detail: { moduleId, lessonId: lesson.id }`.
  - [x] Revisit case (`existing?.status === 'complete'`): no engage/complete events fire on revisit because no transition occurs. `lessonopen` *does* fire (every mount opens). This matches FR-P15's "once per mount, suppressed when no new transition" rule.
  - [x] Choose the event mechanism explicitly: Svelte 5 components emit events via callback props or via DOM `CustomEvent`. Pick the callback-prop pattern (`onlessonopen`, `onlessonengage`, `onlessoncomplete`) for type safety and consistency with existing `onblockcomplete`/`onquizcomplete` props. No subscribers in this story; document the props in the component header.
- [x] `sveltekit_template/src/lib/components/LessonList.svelte`:
  - [x] `statusIcon`: extend the mapping so `'opened'` returns the same icon as `'in_progress'` (`…`).
  - [x] `statusClass`: extend so `'opened'` returns the same class as `'in_progress'` (`text-blue-500`).
  - [x] Implementation note: rather than adding a parallel branch, broaden the existing `s === 'in_progress'` check to `s === 'in_progress' || s === 'opened'` in both helpers. Single-line change in each, minimal diff surface.
  - [x] Helper `lessonStatusIcon` in `module-list.helpers.ts` (if it gates on the same mapping) gets the same broadening.
- [x] `sveltekit_template/src/lib/utils/locking.ts`:
  - [x] `getOptionalLessons` derivation: the unlock-key lesson must be `'complete'`. The `opened` status does NOT trigger optional-sibling cascade — only `complete` does. Verify the existing condition (`progress[mod.id]?.lessons[keyLessonId]?.status === 'complete'`) is unaffected and add a one-line comment to that effect.
  - [x] `isModuleComplete` and `isModuleLocked` derivations: same — `opened` does not contribute to module completeness. Verify and document.
- [x] `sveltekit_template/src/lib/utils/progress.ts` (introduced in I.l):
  - [x] `hasAnyProgress` already returns true for any non-`'not_started'` status. The new `'opened'` status is correctly classified as activity (Reset button enables on first open). Add a test case to lock this in.
- [x] Tests (vitest):
  - [x] `db.progress.test.ts` — new cases: `markLessonOpened` writes `opened` from a fresh state; `markLessonOpened` is idempotent on a row already at `opened` (status preserved); `markLessonOpened` does NOT demote an `in_progress` row; `markLessonOpened` does NOT demote a `complete` row.
  - [x] `db.progress.test.ts` — extend the existing `markLessonInProgress` cases: when called on an `opened` row, status promotes to `in_progress`; when called on a `not_started` row (legacy path), still works — but document that the legacy callers no longer exist after this story.
  - [x] `LessonView.test.ts` — new cases: on mount, `markLessonOpened` is called and `onlessonopen` fires; on first block-complete, `markLessonInProgress` is called and `onlessonengage` fires; on all-blocks-complete, `markLessonComplete` is called and `onlessoncomplete` fires; mounting a lesson already at `complete` calls `markLessonOpened` and fires only `onlessonopen` (no engage, no complete); zero-block lesson fires `onlessonopen` and `onlessoncomplete` in order.
  - [x] `LessonList.test.ts` — `opened` status renders `…` icon and `text-blue-500` class.
  - [x] `progress.utils.test.ts` — `hasAnyProgress` returns `true` when a single lesson is at status `'opened'` and all others are `'not_started'`.
- [x] Playwright e2e (extends I.k/I.o harness):
  - [x] `e2e/lifecycle.spec.ts` (new): navigate to lesson 1 → assert sidebar icon for lesson 1 transitions from `○` to `…` within ~100 ms (this is the `opened` status, indistinguishable from `in_progress` per FR-P15's UI mapping). Wait long enough for the first text-block sentinel to fire → the icon stays `…` (now via `in_progress` underlying status; visual unchanged). Engage all blocks → icon becomes `✓`. The visual sequence is `○ → … → ✓` for the learner; the data sequence underneath is `not_started → opened → in_progress → complete`.
- [x] Mirror all `sveltekit_template/` changes to `src/learningfoundry/sveltekit_template/`.
- [x] `docs/specs/features.md` — under FR-4 (Progress Tracking) document the four-state lesson lifecycle (`not_started`, `opened`, `in_progress`, `complete`) and note that `opened` and `in_progress` share a sidebar icon. Note the three custom-event emitters and that no internal subscribers exist today (forward-compatible hooks).
- [x] `docs/specs/tech-spec.md` — update the Data Models / Progress Tracking section to reflect the extended `LessonStatus` enum and the new `markLessonOpened` DB op.
- [x] `docs/specs/project-essentials.md` — add a one-line note under "Domain Conventions" documenting the four-state lesson status sequence and that `opened` and `in_progress` are visually merged.
- [x] Bump version to v0.51.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] `CHANGELOG.md` — v0.51.0 under "Added" (lesson `opened` status, three custom lifecycle events `lessonopen` / `lessonengage` / `lessoncomplete`, `markLessonOpened` DB op) and "Changed" (`markLessonInProgress` is now called on the first block-engagement event rather than on mount; sidebar icon mapping broadened so `opened` shows `…`).
- [x] Verify: `pyve test`, `pyve test tests/test_smoke_sveltekit.py`, `pnpm test`, `pnpm e2e`, `ruff`, `mypy`.

**Out of scope:**
- `lessonresume` event (revisits to lessons already at `complete`) — recorded in Future.
- Lifecycle timestamps (`opened_at`, `engaged_at`, …) — adding them just for the new transitions would create asymmetric coverage with the existing `completed_at`. A full "lifecycle timestamps" treatment (covering all transitions consistently, with retention/decimation policies) is its own story; not this one.
- Distinct sidebar icon for `opened` (kept the same `…` as `in_progress` per the design decision in FR-P15 / Q2).
- Analytics / telemetry adapters that subscribe to the new events — the events exist as forward-compatible hooks; consumers come later.
- Per-block lifecycle events at the same level of granularity (e.g. `blockopen`). The block-completion model is already covered by FR-P1; expanding it to mirror lesson lifecycle is out of scope.

---

### Story I.q: v0.52.0 — Vitest Component Mount Support for Svelte 5 [Planned]

Stories I.o and I.p both deferred component-level vitest coverage with the same root-cause caveat: mounting a Svelte 5 component inside vitest's jsdom environment trips `lifecycle_function_unavailable` (`mount(...) is not available on the server`), and falling back to Svelte's server `render` API trips `get_first_child` because the SvelteKit vite plugin compiles the component in client mode regardless. As a result, several test goals from those stories were either skipped, downgraded to source-text assertions (`TextBlock.observer.test.ts`), or relegated to the e2e layer (`LessonView` lifecycle event firing, `VideoBlock` URL-change re-mount). The e2e layer eventually catches these regressions, but the feedback loop is minutes (full pnpm install + Playwright + browser launch) instead of seconds, and the e2e harness is skipped entirely when Chromium isn't installed.

The conventional fix for Svelte 5 + vitest is to add `resolve.conditions: ['browser']` to the vite config so vitest resolves `svelte` to its browser entry point. This must be guarded behind `process.env.VITEST` (or vitest's own conditional config) so it does not affect production `vite build`. With that in place, mounting via `@testing-library/svelte` works in jsdom and component-level assertions become a normal part of the unit-test layer.

This is a foundation story: no new product behaviour ships, but the testability ceiling is raised for every subsequent component-touching story. Scope is intentionally minimal — wire the config, prove the path with one previously-deferred test, document the pattern. Backporting deferred coverage from I.o and I.p is a follow-up story so this one stays focused.

**Tasks:**

- [ ] `sveltekit_template/vite.config.ts`:
  - [ ] Add a vitest-only `resolve.conditions: ['browser']` block guarded by `process.env.VITEST` so production `vite build` is unaffected. Document the guard with a one-line comment pointing at this story / FR-P15-Q3 (Svelte 5 mount in jsdom).
  - [ ] Verify the existing `test: { environment: 'jsdom' }` block stays put — the fix is at the resolution layer, not the environment layer.
- [ ] `sveltekit_template/package.json`:
  - [ ] Add `@testing-library/svelte` as a dev dependency (re-add what was removed in I.o once the config supports it).
  - [ ] Add `@testing-library/jest-dom` if `expect(...).toBeInTheDocument()` style matchers are wanted; otherwise skip and use plain DOM assertions.
- [ ] `sveltekit_template/src/lib/components/TextBlock.observer.test.ts` (rewrite):
  - [ ] Replace the source-text assertions with a real mount: render `<TextBlock>` via `@testing-library/svelte`, stub `IntersectionObserver` to capture the observed element, assert (a) the captured element has `[data-textblock-end]` and (b) `getBoundingClientRect().height > 0` (or the inline `style.height === '1px'` if jsdom doesn't lay out reliably).
  - [ ] Keep the source-text assertions in place during the transition if useful, or delete them — the mount test is strictly stronger.
- [ ] `sveltekit_template/src/lib/components/mount.test.ts` (new, smoke):
  - [ ] One trivial test that mounts the simplest possible component (e.g. a fresh inline `<button>Hi</button>` Svelte component or a re-mount of an existing leaf like `ProgressBar`) and asserts the resulting DOM. Smoke check that the resolve-conditions fix is in place and didn't silently revert.
- [ ] `docs/specs/project-essentials.md`:
  - [ ] Add a one-paragraph entry under "Workflow Rules" or a new "Testing" subsection: "Svelte 5 component mounts in vitest require `resolve.conditions: ['browser']` in `vite.config.ts`. Don't remove the `process.env.VITEST` guard — production `vite build` must not pick up the browser conditions or it will mis-bundle SSR-only code paths."
- [ ] Verify by re-enabling one previously-deferred test (and only one — others are follow-up scope):
  - [ ] Re-instate the FR-P15 / Story I.p `LessonView.test.ts` "on mount, `markLessonOpened` is called and `onlessonopen` fires" case via real mount + mock DB. Assert the call ordering: `markLessonOpened` resolves before `onlessonopen` fires.
- [ ] Mirror all `sveltekit_template/` changes to `src/learningfoundry/sveltekit_template/`.
- [ ] Bump version to v0.52.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [ ] `CHANGELOG.md` — v0.52.0 under "Added" (Svelte 5 component mount support in vitest; `@testing-library/svelte` dev dependency restored; one re-instated `LessonView` mount test) and "Changed" (`vite.config.ts` adds `resolve.conditions: ['browser']` under `process.env.VITEST`).
- [ ] Verify: `pyve test`, `pyve test tests/test_smoke_sveltekit.py`, `pnpm test`, `pnpm e2e`, `ruff`, `mypy`. Confirm `pnpm build` still produces a working static site (the resolve-conditions guard must not leak into production builds).

**Out of scope:**

- Backporting every deferred component-level test from I.o (`VideoBlock` URL-change re-mount, full real-DOM `TextBlock` observer interaction) and I.p (the four `LessonView` lifecycle test cases beyond the one re-instated above). Each is its own follow-up; this story proves the path and stops.
- Migrating to vitest's "browser" environment (`@vitest/browser` + Playwright). Heavier, slower, requires browser binaries — only worth doing if jsdom + `resolve.conditions` proves insufficient for some specific test. If that comes up, it gets its own story.
- Visual regression / screenshot testing infrastructure.
- Restructuring vitest into projects (server suite vs. client suite). Single-suite + browser conditions covers every test in the codebase today; projects are over-engineering until a Svelte 5 server-render test arrives.
- Re-evaluating Storybook or other component-rendering harnesses.

---

## Future

<!--
This section captures items intentionally deferred from the active phases above:
- Stories not yet planned in detail
- Phases beyond the current scope
- Project-level out-of-scope items
The `archive_stories` mode preserves this section verbatim when archiving stories.md.
-->

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
