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

### Story I.g: v0.42.0 — Block Completion Events and Lesson Auto-Complete [Planned]

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

- [ ] `sveltekit_template/src/lib/stores/progress.ts` (new):
  - [ ] `progressStore`: writable `Record<string, ModuleProgress>`, initialised `{}`
  - [ ] `invalidateProgress(curriculum: Curriculum | null): Promise<void>`: fetches all module progress and writes to store; no-op if `curriculum` is null
  - [ ] Export both
- [ ] `sveltekit_template/src/routes/+layout.svelte`:
  - [ ] Replace the one-shot `$effect` progress fetch with a subscription to `progressStore`
  - [ ] Call `invalidateProgress($curriculum)` when `$curriculum` becomes non-null
- [ ] `sveltekit_template/src/lib/components/TextBlock.svelte`:
  - [ ] On mount, create `IntersectionObserver`; when block enters viewport start a 1-second timer; cancel timer if block leaves viewport before 1 s; when timer fires, dispatch `textcomplete` (once only — guard against double-fire)
  - [ ] Clean up observer and timer on component destroy
- [ ] `sveltekit_template/src/lib/components/VideoBlock.svelte`:
  - [ ] Inject YouTube IFrame API script tag if `window.YT` is not already loaded; wait for `window.onYouTubeIframeAPIReady`
  - [ ] Create `YT.Player` on the video container; register `onStateChange` callback; when `event.data === YT.PlayerState.ENDED` dispatch `videocomplete` (once only)
  - [ ] Fallback: if IFrame API not ready within 5 s, attach Intersection Observer with 3-second threshold instead
  - [ ] Clean up player and observer on destroy
- [ ] `sveltekit_template/src/lib/components/ContentBlock.svelte`:
  - [ ] Listen for `textcomplete`, `videocomplete`, `quizcomplete` from child components
  - [ ] Forward each as a `blockcomplete` custom event with `detail: { blockIndex: number }` to the parent `LessonView`
  - [ ] Pass `passThreshold` from quiz block content to the `<QuizBlock>` component
- [ ] `sveltekit_template/src/lib/components/LessonView.svelte`:
  - [ ] On mount: call `getLessonProgress(moduleId, lesson.id)`; if status is `complete`, set `allBlocksComplete = true` immediately; otherwise initialise `completedBlocks = new Set<number>()`
  - [ ] Handle `blockcomplete` events from `ContentBlock`: add `blockIndex` to `completedBlocks`; when `completedBlocks.size === lesson.content_blocks.length`, call `markLessonComplete(moduleId, lesson.id)` then `invalidateProgress($curriculum)`
  - [ ] Derive `lessonComplete`: `allBlocksComplete || completedBlocks.size === lesson.content_blocks.length`
  - [ ] Handle zero-block case: `lessonComplete = true` on mount if `lesson.content_blocks.length === 0`
  - [ ] Pass `disabled={!lessonComplete}` to `<Navigation>`
  - [ ] Remove `handleNavComplete` and `oncomplete` prop (no longer needed)
- [ ] `sveltekit_template/src/lib/components/Navigation.svelte`:
  - [ ] Accept `disabled: boolean` prop (default `false`)
  - [ ] Apply `disabled` attribute and `opacity-50 cursor-not-allowed` style to Next/Finish button when `disabled`
  - [ ] `goNext()`: if `next` → `navigateTo(next.moduleId, next.lessonId)`; else → `goto('/')` (import `goto` from `$app/navigation`)
  - [ ] Remove `onComplete` prop — Finish now routes directly
- [ ] `sveltekit_template/src/lib/types/index.ts`:
  - [ ] `QuizContent` interface gains `passThreshold?: number`
- [ ] Tests (vitest):
  - [ ] `TextBlock.test.ts`: fires `textcomplete` after 1 s in viewport; does NOT fire if block leaves before 1 s; fires on first qualifying viewport interval only (no double-fire)
  - [ ] `VideoBlock.test.ts`: mock `YT` global; ENDED state fires `videocomplete`; fallback: viewport 3 s fires `videocomplete` when YT API absent
  - [ ] `LessonView.test.ts`: all blocks complete → `markLessonComplete` called and `invalidateProgress` called; button disabled until all blocks done; pre-fills set when lesson is already `complete`; zero-block lesson is immediately complete
  - [ ] `progress.store.test.ts`: `invalidateProgress` writes fetched data to store; subsequent calls overwrite not append
- [ ] Mirror all changes to `src/learningfoundry/sveltekit_template/`
- [ ] Bump version to v0.42.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`
- [ ] `CHANGELOG.md` — v0.42.0 under "Added" (block completion events, lesson auto-complete, reactive progress store) and "Changed" (Next/Finish no longer trigger completion marking)
- [ ] Verify: `pyve test`, `pyve test tests/test_smoke_sveltekit.py`, `ruff`, `mypy`

**Out of scope:**
- Non-YouTube video providers (IFrame API is YouTube-specific; other providers use the viewport fallback until their own story)
- Per-lesson scroll memory on revisit

---

### Story I.h: v0.43.0 — Dashboard Curriculum Progress Bar [Planned]

The dashboard (`/`) displays per-module progress bars but no curriculum-level summary. Add a single bar above the module cards showing overall completion. Depends on the reactive `progressStore` introduced in I.g.

**Display:**
```
12 of 40 lessons completed
[████████░░░░░░░░░░░░░░░░]
```

Computed from the reactive store as `sum(complete lessons across all modules) / sum(all lessons across all modules)`. Updates live when lessons complete during the session — no page reload required.

**Tasks:**

- [ ] `sveltekit_template/src/lib/components/ProgressDashboard.svelte`:
  - [ ] Compute `totalLessons = modules.reduce((n, m) => n + m.lessons.length, 0)`
  - [ ] Compute `totalComplete = modules.reduce((n, m) => n + completeLessonCount(m, progress), 0)` where `completeLessonCount` counts lessons with status `complete`
  - [ ] Render a `<ProgressBar percent={...}>` with label `"{totalComplete} of {totalLessons} lessons completed"` above the existing module card list
  - [ ] Handle `totalLessons === 0` gracefully (no division by zero; hide bar or show 0%)
- [ ] `sveltekit_template/src/routes/+page.svelte` (dashboard route):
  - [ ] Confirm it passes `modules` and the reactive `progress` from `progressStore` to `ProgressDashboard` (wire if missing)
- [ ] Tests (vitest):
  - [ ] `ProgressDashboard.test.ts`: bar shows 0% when no lessons complete; bar shows 50% when half complete; bar shows 100% when all complete; label text is correct
- [ ] Mirror changes to `src/learningfoundry/sveltekit_template/`
- [ ] Bump version to v0.43.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`
- [ ] `CHANGELOG.md` — v0.43.0 under "Added"
- [ ] Verify: `pyve test`, smoke, `ruff`, `mypy`

**Out of scope:**
- Curriculum completion celebration / "Course Complete" screen (future story)
- Cross-module progress export

---

### Story I.i: v0.44.0 — Locking Configuration Schema [Planned]

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

- [ ] `src/learningfoundry/schema_v1.py`:
  - [ ] New `LockingConfig` Pydantic model: `sequential: bool = False`, `lesson_sequential: bool = False`
  - [ ] `CurriculumSchema` gains `locking: LockingConfig = Field(default_factory=LockingConfig)`
  - [ ] `ModuleSchema` gains `locked: Optional[bool] = None` (None = inherit)
  - [ ] `LessonSchema` gains `unlock_module_on_complete: bool = False`
  - [ ] `QuizBlock` gains `pass_threshold: float = Field(0.0, ge=0.0, le=1.0)`
- [ ] `src/learningfoundry/resolver.py`:
  - [ ] `ResolvedCurriculum` carries `locking: LockingConfig`
  - [ ] `ResolvedModule` carries `locked: Optional[bool]`
  - [ ] `ResolvedLesson` carries `unlock_module_on_complete: bool`
  - [ ] Resolved quiz content dict includes `pass_threshold` key
- [ ] `src/learningfoundry/generator.py`:
  - [ ] `curriculum.json` output includes top-level `locking` object, per-module `locked`, per-lesson `unlock_module_on_complete`, and per-quiz content `pass_threshold`
- [ ] Global config (`config.py` or equivalent):
  - [ ] Add `locking: LockingConfig` block to global config schema with defaults `sequential=False, lesson_sequential=False`
  - [ ] Merge order: global config → curriculum YAML `locking`; per-module `locked` is a separate direct override, not part of the `LockingConfig` merge
- [ ] `tests/test_schema_v1.py`:
  - [ ] `LockingConfig` defaults: both fields False
  - [ ] `pass_threshold` validates 0.0–1.0; rejects values outside range
  - [ ] `unlock_module_on_complete` defaults False; round-trips True
  - [ ] `locked: null` (absent), `locked: false`, `locked: true` all parse correctly
  - [ ] Full curriculum with locking fields round-trips through parse → serialize
- [ ] `tests/test_resolver.py`:
  - [ ] Locking fields appear in resolved curriculum output
  - [ ] Quiz `pass_threshold` propagated into content dict
  - [ ] `unlock_module_on_complete` propagated onto resolved lesson
- [ ] `tests/test_smoke_sveltekit.py`:
  - [ ] `curriculum.json` includes `locking`, `locked`, `unlock_module_on_complete`, `pass_threshold`
- [ ] `tests/fixtures/valid-curriculum.yml`:
  - [ ] Add top-level `locking:` block and one lesson with `unlock_module_on_complete: true` and one quiz block with `pass_threshold: 0.5`
- [ ] `docs/specs/features.md`:
  - [ ] FR-1 (YAML Parsing): document `LockingConfig`, `locked`, `unlock_module_on_complete`, `pass_threshold`
  - [ ] FR-4 (Progress Tracking): add sub-section on locking config and how sequential access is enforced
- [ ] `docs/specs/tech-spec.md`:
  - [ ] Schema section: `LockingConfig` model, new fields on `CurriculumSchema`, `ModuleSchema`, `LessonSchema`, `QuizBlock`
  - [ ] Data Models section: `ResolvedCurriculum.locking`, `ResolvedModule.locked`, `ResolvedLesson.unlock_module_on_complete`
- [ ] `README.md` — new "Content locking" subsection under Curriculum YAML Format documenting the three-level hierarchy and `unlock_module_on_complete`
- [ ] Bump version to v0.44.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`
- [ ] `CHANGELOG.md` — v0.44.0 under "Added"
- [ ] Verify: `pyve test`, smoke, `ruff`, `mypy`

**Out of scope:**
- Frontend locking UI (Story I.j)
- Reset button

---

### Story I.j: v0.45.0 — Locking and Unlocking UI [Planned]

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

- [ ] `sveltekit_template/src/lib/types/index.ts`:
  - [ ] `LessonStatus` gains `'optional'`
  - [ ] `Lesson` interface gains `unlockModuleOnComplete?: boolean`
  - [ ] `Module` interface gains `locked?: boolean`
  - [ ] `Curriculum` interface gains `locking?: LockingConfig`
  - [ ] New `LockingConfig` TypeScript interface: `{ sequential: boolean; lessonSequential: boolean }`
- [ ] `sveltekit_template/src/lib/utils/locking.ts` (new):
  - [ ] `resolveLocking(curriculum, globalLocking)`: returns effective `LockingConfig` (curriculum overrides global; per-module `locked` is a separate pass)
  - [ ] `isModuleLocked(moduleIndex, curriculum, progress, globalLocking): boolean`: locked if (a) explicit `module.locked === true`, or (b) sequential mode + previous module not complete; first module is never locked by sequential rule alone
  - [ ] `isLessonLocked(moduleId, lessonIndex, curriculum, progress, globalLocking): boolean`: locked if lesson_sequential mode and previous lesson in same module not complete
  - [ ] `getOptionalLessons(moduleId, curriculum, progress): Set<string>`: returns IDs of sibling lessons that are optional (key lesson for this module is `complete` in progress)
  - [ ] `isModuleComplete(moduleId, curriculum, progress): boolean`: all non-optional lessons are `complete` (uses `getOptionalLessons` to exclude optional lessons from the requirement)
- [ ] `sveltekit_template/src/routes/+layout.svelte`:
  - [ ] Import `isModuleLocked`, `isLessonLocked`, `getOptionalLessons` from `$lib/utils/locking.ts`
  - [ ] Derive per-module locked state and per-lesson locked/optional state from `$curriculum`, `$progressStore`, and global config
  - [ ] Pass derived locked/optional state to `<ModuleList>`
- [ ] `sveltekit_template/src/lib/components/ModuleList.svelte`:
  - [ ] Accept `lockedModules: Set<string>` prop
  - [ ] Locked module card: `onclick` is no-op; `aria-disabled="true"`; show `<Lock size={14}>` (Lucide) next to module title; do not render `<LessonList>` or `<ProgressBar>` expand panel
  - [ ] Do not apply active-module highlight to a locked module
- [ ] `sveltekit_template/src/lib/components/LessonList.svelte`:
  - [ ] Accept `optionalLessons: Set<string>` and `lockedLessons: Set<string>` props (both default `new Set()`)
  - [ ] Locked lesson: `cursor-not-allowed text-gray-300`; click handler is no-op
  - [ ] Optional lesson: `statusIcon` returns `◇`; `statusClass` returns `text-gray-400`
  - [ ] Update `statusIcon` and `statusClass` to handle `optional` status (from progress store) and locked override (from `lockedLessons` prop)
- [ ] `sveltekit_template/src/lib/components/LessonView.svelte`:
  - [ ] After `markLessonComplete` and `invalidateProgress`, check `lesson.unlockModuleOnComplete`; if true, call `invalidateProgress($curriculum)` again (the progress store re-derive will pick up the new `complete` status and `getOptionalLessons` / `isModuleLocked` will return the updated state automatically — no extra DB write needed)
- [ ] `sveltekit_template/src/lib/components/ProgressDashboard.svelte`:
  - [ ] Accept `optionalLessons` per module; use `isModuleComplete` for per-module status badge (excludes optional lessons from requirement)
  - [ ] Curriculum-level bar: continue counting all completed lessons (optional or not) toward `totalComplete`
- [ ] Tests (vitest):
  - [ ] `locking.test.ts`:
    - [ ] `isModuleLocked`: first module never locked; second module locked when sequential + first module incomplete; unlocked when first module complete; `locked: false` override beats sequential rule; `locked: true` override forces locked even when previous complete
    - [ ] `isLessonLocked`: lesson 2 locked when `lessonSequential` + lesson 1 incomplete; unlocked when lesson 1 complete
    - [ ] `getOptionalLessons`: returns empty set before key lesson complete; returns all sibling IDs after key lesson complete
    - [ ] `isModuleComplete`: false while non-optional lessons incomplete; true when all non-optional done; optional lessons do not block completion
  - [ ] `ModuleList.test.ts`: locked module header click is no-op; lock icon rendered; lesson list not rendered for locked module
  - [ ] `LessonList.test.ts`: locked lesson click is no-op; optional lesson shows `◇`; complete lesson shows `✓`
- [ ] Mirror all changes to `src/learningfoundry/sveltekit_template/`
- [ ] Bump version to v0.45.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`
- [ ] `CHANGELOG.md` — v0.45.0 under "Added"
- [ ] Verify: `pyve test`, smoke, `ruff`, `mypy`

**Out of scope:**
- Reset button (course / module / lesson)
- Tooltip/explanation when learner clicks a locked lesson
- Animated unlock transition
- Lesson-level `locked: bool` override (module-level and sequential rules cover v1 cases)

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
- **Spaced repetition / adaptive sequencing**
- **Multi-curriculum dashboard**
