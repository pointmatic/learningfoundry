# stories.md -- learningfoundry (python)

This document breaks the `learningfoundry` project into an ordered sequence of small, independently completable stories grouped into phases. Each story has a checklist of concrete tasks. Stories are organized by phase and reference modules defined in `tech-spec.md`.

Stories with code changes include a version number (e.g., v0.1.0). Stories with only documentation or polish changes omit the version number. The version follows semantic versioning and is bumped per story. Stories are marked with `[Planned]` initially and changed to `[Done]` when completed.

For a high-level concept (why), see `concept.md`. For requirements and behavior (what), see `features.md`. For implementation details (how), see `tech-spec.md`. For project-specific must-know facts, see `project-essentials.md` (`plan_phase` appends new facts per phase).

> **Convention change (Story I.r, v0.53.0):** the workspace-root `sveltekit_template/` duplicate was removed. The package-internal copy at `src/learningfoundry/sveltekit_template/` is now the single source of truth — that's the path `generator.py` reads at runtime and the path stories should target. Do NOT add "Mirror to `src/learningfoundry/sveltekit_template/`" tasks to new stories; the prior phrasing inverted cause and effect and let the two copies drift. Existing `[Done]` story checklists keep their historical mirror tasks as a record of what happened at the time.

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

### Story I.q: v0.52.0 — Vitest Component Mount Support for Svelte 5 [Done]

Stories I.o and I.p both deferred component-level vitest coverage with the same root-cause caveat: mounting a Svelte 5 component inside vitest's jsdom environment trips `lifecycle_function_unavailable` (`mount(...) is not available on the server`), and falling back to Svelte's server `render` API trips `get_first_child` because the SvelteKit vite plugin compiles the component in client mode regardless. As a result, several test goals from those stories were either skipped, downgraded to source-text assertions (`TextBlock.observer.test.ts`), or relegated to the e2e layer (`LessonView` lifecycle event firing, `VideoBlock` URL-change re-mount). The e2e layer eventually catches these regressions, but the feedback loop is minutes (full pnpm install + Playwright + browser launch) instead of seconds, and the e2e harness is skipped entirely when Chromium isn't installed.

The conventional fix for Svelte 5 + vitest is to add `resolve.conditions: ['browser']` to the vite config so vitest resolves `svelte` to its browser entry point. This must be guarded behind `process.env.VITEST` (or vitest's own conditional config) so it does not affect production `vite build`. With that in place, mounting via `@testing-library/svelte` works in jsdom and component-level assertions become a normal part of the unit-test layer.

This is a foundation story: no new product behaviour ships, but the testability ceiling is raised for every subsequent component-touching story. Scope is intentionally minimal — wire the config, prove the path with one previously-deferred test, document the pattern. Backporting deferred coverage from I.o and I.p is a follow-up story so this one stays focused.

**Tasks:**

- [x] `sveltekit_template/vite.config.ts`:
  - [x] Add a vitest-only `resolve.conditions: ['browser']` block guarded by `process.env.VITEST` so production `vite build` is unaffected. Document the guard with a one-line comment pointing at this story / FR-P15-Q3 (Svelte 5 mount in jsdom).
  - [x] Verify the existing `test: { environment: 'jsdom' }` block stays put — the fix is at the resolution layer, not the environment layer.
- [x] `sveltekit_template/package.json`:
  - [x] Add `@testing-library/svelte` as a dev dependency (re-add what was removed in I.o once the config supports it).
  - [x] Add `@testing-library/jest-dom` if `expect(...).toBeInTheDocument()` style matchers are wanted; otherwise skip and use plain DOM assertions.
- [x] `sveltekit_template/src/lib/components/TextBlock.observer.test.ts` (rewrite):
  - [x] Replace the source-text assertions with a real mount: render `<TextBlock>` via `@testing-library/svelte`, stub `IntersectionObserver` to capture the observed element, assert (a) the captured element has `[data-textblock-end]` and (b) `getBoundingClientRect().height > 0` (or the inline `style.height === '1px'` if jsdom doesn't lay out reliably).
  - [x] Keep the source-text assertions in place during the transition if useful, or delete them — the mount test is strictly stronger.
- [x] `sveltekit_template/src/lib/components/mount.test.ts` (new, smoke):
  - [x] One trivial test that mounts the simplest possible component (e.g. a fresh inline `<button>Hi</button>` Svelte component or a re-mount of an existing leaf like `ProgressBar`) and asserts the resulting DOM. Smoke check that the resolve-conditions fix is in place and didn't silently revert.
- [x] `docs/specs/project-essentials.md`:
  - [x] Add a one-paragraph entry under "Workflow Rules" or a new "Testing" subsection: "Svelte 5 component mounts in vitest require `resolve.conditions: ['browser']` in `vite.config.ts`. Don't remove the `process.env.VITEST` guard — production `vite build` must not pick up the browser conditions or it will mis-bundle SSR-only code paths."
- [x] Verify by re-enabling one previously-deferred test (and only one — others are follow-up scope):
  - [x] Re-instate the FR-P15 / Story I.p `LessonView.test.ts` "on mount, `markLessonOpened` is called and `onlessonopen` fires" case via real mount + mock DB. Assert the call ordering: `markLessonOpened` resolves before `onlessonopen` fires.
- [x] Mirror all `sveltekit_template/` changes to `src/learningfoundry/sveltekit_template/`.
- [x] Bump version to v0.52.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] `CHANGELOG.md` — v0.52.0 under "Added" (Svelte 5 component mount support in vitest; `@testing-library/svelte` dev dependency restored; one re-instated `LessonView` mount test) and "Changed" (`vite.config.ts` adds `resolve.conditions: ['browser']` under `process.env.VITEST`).
- [x] Verify: `pyve test`, `pyve test tests/test_smoke_sveltekit.py`, `pnpm test`, `pnpm e2e`, `ruff`, `mypy`. Confirm `pnpm build` still produces a working static site (the resolve-conditions guard must not leak into production builds).

**Out of scope:**

- Backporting every deferred component-level test from I.o (`VideoBlock` URL-change re-mount, full real-DOM `TextBlock` observer interaction) and I.p (the four `LessonView` lifecycle test cases beyond the one re-instated above). Each is its own follow-up; this story proves the path and stops.
- Migrating to vitest's "browser" environment (`@vitest/browser` + Playwright). Heavier, slower, requires browser binaries — only worth doing if jsdom + `resolve.conditions` proves insufficient for some specific test. If that comes up, it gets its own story.
- Visual regression / screenshot testing infrastructure.
- Restructuring vitest into projects (server suite vs. client suite). Single-suite + browser conditions covers every test in the codebase today; projects are over-engineering until a Svelte 5 server-render test arrives.
- Re-evaluating Storybook or other component-rendering harnesses.

---

### Story I.r: v0.53.0 — Dashboard "Continue" Regression Fix [Done]

`ProgressDashboard.svelte`'s `moduleStats()` derives the per-module button text (`Start module →` vs. `Continue →`) from `done > 0`, where `done` counts only **complete** lessons. A module with an `opened` or `in_progress` lesson — but no completed ones — falls through to "Start module →" even though the sidebar correctly shows the lesson as `…` in-progress. v0.43.0 (Story I.h) used the rollup `mp.status` from `getModuleProgress`, which already correctly returns `'in_progress'` for any non-`not_started` lesson; v0.45.0 (Story I.j) replaced that branch with `done > 0` while introducing the `isModuleComplete` check for optional lessons. The `complete` half got more correct; the `in_progress` half regressed silently. Story I.p (`opened` status, v0.51.0) didn't introduce the bug but made it visible on every lesson click.

The fix: restore the `mp.status === 'in_progress'` check for the in-progress branch; keep the existing `isModuleComplete` check for the complete branch (so optional-lessons handling is unchanged).

**Coverage gap.** The existing `ProgressDashboard.test.ts` cases cover `curriculumTotals` (the curriculum-wide bar math) but no case asserts the per-module button text against an in-progress-but-not-complete state. The unit-level case added below would have caught it; the planned full real-DOM rewrite in Story I.t adds the matching mount-level case.

**Tasks:**

- [x] `src/learningfoundry/sveltekit_template/src/lib/components/ProgressDashboard.svelte` — in `moduleStats()`, replace the `done > 0` branch with `mp.status === 'in_progress'`. The `complete` branch and `isModuleComplete` lookup stay unchanged. Update the inline comment to note the rollup-vs-count semantics so a future "simplify" doesn't re-narrow it.
- [x] `src/learningfoundry/sveltekit_template/src/lib/components/progress-dashboard.helpers.ts` — if a `moduleStatus(mod, progress)` helper exists or is added, exercise it instead so the regression is locked at the helper layer too. If not, skip; the component-level test below is sufficient.
- [x] `src/learningfoundry/sveltekit_template/src/lib/components/ProgressDashboard.test.ts` — add three vitest cases against the existing helper-style harness (real-mount versions land in Story I.t):
  - [x] Module with one `opened` lesson and zero `complete` lessons → status is `'in_progress'`, label is `'Continue →'`.
  - [x] Module with one `in_progress` lesson and zero `complete` lessons → status is `'in_progress'`, label is `'Continue →'`.
  - [x] Module with zero touched lessons → status is `'not_started'`, label is `'Start module →'` (regression-lock for the previously-correct path).
- [x] Bump version to v0.53.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] `CHANGELOG.md` — v0.53.0 under "Fixed" (dashboard "Start module" wrongly displayed for modules with opened/in-progress lessons; regression from v0.45.0 surfaced by v0.51.0), "Removed" (workspace-root `sveltekit_template/` duplicate; package copy is the single source of truth), and "Changed" (story-template language; `project-essentials.md` source-of-truth path).
- [x] Verify: `pyve test`, `pyve test tests/test_smoke_sveltekit.py` (must include `pnpm test` + `pnpm build` succeeding against the package copy), `ruff`, `mypy`. The smoke test is the canonical check for Part 1 — if it passes, the deletion is safe.

**Out of scope:**

- Real-mount `ProgressDashboard` tests asserting the rendered "Continue" / "Start module" link text. That's Story I.t's scope; the helper-style cases added here are sufficient anti-regression coverage in the meantime.
- Auditing other components for the same `done > 0` vs. `mp.status === 'in_progress'` mismatch. The rollup-vs-count distinction is specific to `ProgressDashboard`; sidebar `ModuleList` already reads `mp.status` correctly.

---

### Story I.s: v0.53.0 — Delete Dead Workspace-Root sveltekit_template Duplicate [Done]

The repository carries two copies of the SvelteKit template: `sveltekit_template/` at the workspace root and `src/learningfoundry/sveltekit_template/` inside the package. Only the package copy runs at runtime — `generator.py` does `_TEMPLATE_DIR = Path(__file__).parent / "sveltekit_template"` and `_atomic_copy()`s that into the user's `build/` output. The root copy is dead code: nothing reads it.

**Origin (verified from git history):** the root copy was the original location in v0.12.0; `generator.py` walked up to it via `Path(__file__).parent.parent.parent / "sveltekit_template"`. v0.25.0 ("Final Polish and Release Prep") copied the template *into* the package so it would ship inside the PyPI wheel and changed `_TEMPLATE_DIR` to the in-package path. The root copy was supposed to be deleted at that point but wasn't. Every story since has carried a "mirror to `src/learningfoundry/sveltekit_template`" task — phrasing inverted from runtime reality, which has caused steady confusion and steady drift. The two copies already differ on `curriculum.ts`, `+layout.svelte`, `app.css`, and `markdown.ts`; several test files exist only in the package version.

**Verified zero runtime/CI/IDE coupling:** no Python source references the root path, no GitHub workflow references either copy, no `.vscode/settings.json` reference. `pyproject.toml`'s coverage `omit = ["*/sveltekit_template/*"]` and `.gitignore`'s `**/sveltekit_template/static/sql-wasm.wasm` match both copies and remain valid after deletion.

The fix: delete the workspace-root copy and update story-template language so future work doesn't reintroduce the mirroring step.

**Tasks:**

- [x] Delete `sveltekit_template/` (the workspace-root directory, **not** `src/learningfoundry/sveltekit_template/`).
- [x] Verify `generator.py`'s `_TEMPLATE_DIR` is unchanged (`Path(__file__).parent / "sveltekit_template"`) — no code change required, just confirmation.
- [x] `docs/specs/stories.md` — when adding subsequent stories, drop the "Mirror all `sveltekit_template/` changes to `src/learningfoundry/sveltekit_template/`" task. Existing `[Done]` story checklists keep their historical mirror tasks (they record what happened); only the template language for new stories changes. Add a note at the top of the document noting this convention change.
- [x] `docs/specs/project-essentials.md` — under "Architecture Quirks" the existing entry says "`sveltekit_template/` is the source of truth: The generated SvelteKit project in `build/` is a copy produced by `generator.py`. Never edit files in the output directory — always edit `sveltekit_template/` and re-run `learningfoundry build`." Update the path to `src/learningfoundry/sveltekit_template/` and add a one-line clarification that the workspace-root duplicate was removed in v0.53.0 to prevent drift.
- [x] `docs/specs/phase-I-progress-ux-subplan.md:200` — the relative-path link `../../sveltekit_template/src/lib/components/LessonView.svelte` resolves to the to-be-deleted root copy from this doc's directory. Repoint to `../../src/learningfoundry/sveltekit_template/src/lib/components/LessonView.svelte`.
- [x] CHANGELOG entries that mention "workspace-root `sveltekit_template/` kept in sync" stay as historical record — those entries describe what happened at the time and should not be rewritten.
- [x] Bump version to v0.53.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`. (Shipped together with Story I.r in the same v0.53.0 release; the story split happened mid-execution and the deletion was already done in the same commit as the dashboard fix.)
- [x] `CHANGELOG.md` — v0.53.0 under "Removed" (workspace-root `sveltekit_template/` duplicate; package copy is the single source of truth) and "Changed" (story-template language; `project-essentials.md` source-of-truth path). The "Fixed" entry referenced here was for the dashboard regression and is covered by Story I.r's CHANGELOG entry under the same v0.53.0 heading.
- [x] Verify: `pyve test`, `pyve test tests/test_smoke_sveltekit.py` (must include `pnpm test` + `pnpm build` succeeding against the package copy), `ruff`, `mypy`. The smoke test is the canonical check for Part 1 — if it passes, the deletion is safe.

**Out of scope:**

- Restructuring `pyproject.toml`'s coverage glob or `.gitignore` patterns. The current globs match both copies; they continue to work after the root copy is gone with no false positives.
- Auditing every relative-path doc link for unrelated dead references. Only fix ones that point at the deleted directory.
- Migrating the package copy to a different location (e.g. `src/learningfoundry/templates/sveltekit/`). The current package-internal path is fine; renaming has no upside and breaks every link in the `[Done]` history.
- Adding a `pre-commit` hook to prevent re-creating the workspace-root copy. If someone re-creates it intentionally they'll have a reason; if they re-create it by accident the story-template language change in this story is the leading defence.

---
### Story I.t: v0.54.0 — Backfill Lesson-Render-Pipeline Real-DOM Tests [Done]

Stories I.k, I.m, I.o, and I.p deferred component-level mount coverage on the lesson-rendering pipeline because Svelte 5 + vitest mounting wasn't supported until Story I.q (v0.52.0). With the resolve-conditions config now in place and proven by [mount.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/mount.test.ts), the deferred coverage on the highest-regression-risk components (`TextBlock`, `VideoBlock`, `LessonView`) can land without infrastructure work. These three components hit two real-world regressions in the last fortnight (the v0.48.0 zero-area sentinel; the v0.46.0 stale-video-iframe), both of which the helper-style tests passed through unaware. Real-DOM coverage is what would have caught either at the unit-test layer.

The existing helper-style tests stay — they remain useful for debugging the timer/debounce logic in isolation. This story adds parallel real-mount tests that exercise the markup and the runtime observer / player wiring.

**Tasks:**

- [x] `sveltekit_template/src/lib/components/TextBlock.observer.test.ts` (extend, do not delete I.q's coverage):
  - [x] Add a case that simulates the `IntersectionObserver` callback firing with `isIntersecting: true` for the captured sentinel target, advances fake timers by 1 s, and asserts `ontextcomplete` was invoked exactly once. The current I.q tests verify *which* element is observed and that it has the right shape; this case verifies the runtime callback path the observer would actually take.
  - [x] Add a case that simulates `isIntersecting: true` followed by `isIntersecting: false` before 1 s elapses, advances timers, and asserts `ontextcomplete` was NOT invoked (regression-lock for the early-leave cancel path).
  - [x] Capture the observer-callback function via the `IntersectionObserver` constructor stub: `vi.stubGlobal('IntersectionObserver', ...)` where the fake records both the target and the callback so the test can drive it directly.
- [x] `sveltekit_template/src/lib/components/VideoBlock.test.ts` (rewrite from helper-only to mount-based):
  - [x] Keep the existing `createViewportTracker` cases — they still document the fallback timer logic.
  - [x] New case: mount `<VideoBlock>` with a YouTube URL, assert `(window as any).YT` script-tag injection happened (via `document.querySelector('script[src*="youtu≥be.com/iframe_api"]')`) and that the `[id^="yt-player-"]` placeholder element rendered.
  - [x] New case: mount with one URL, then re-render with a different URL via prop update; capture `YT.Player` calls (stubbed) and assert (a) the previous player's `destroy()` was called, (b) a new player was created with the new `videoId` extracted from the new URL, (c) the internal `fired` flag was reset (proxy: `onvideocomplete` can fire again on the new player's `ENDED` state). Use `vi.useFakeTimers()` and `vi.stubGlobal('YT', ...)` per the existing pattern.
  - [x] New case: mount without `window.YT`; advance timers past the 5 s fallback threshold; assert the viewport-fallback `IntersectionObserver` was attached to the wrapper element. (Catches the regression where the fallback path silently breaks.)
- [x] `sveltekit_template/src/lib/components/LessonView.test.ts` (extend; the I.q ordering case stays):
  - [x] New case: mount `<LessonView>` with one block, simulate a `blockcomplete` event, assert `markLessonInProgress` was called and `onlessonengage` fired with `{moduleId, lessonId}`. (FR-P15 engage transition.)
  - [x] New case: mount with two blocks, simulate `blockcomplete` for both, assert `markLessonComplete` was called, `invalidateProgress` was called with the curriculum, and `onlessoncomplete` fired. (FR-P15 complete transition.)
  - [x] New case: stub `getLessonProgress` to return `{status: 'complete'}`; mount; assert `markLessonOpened` and `onlessonopen` fire (every mount opens), but `onlessonengage` and `onlessoncomplete` do NOT fire — no transition occurs on revisit. (FR-P15 revisit suppression.)
  - [x] New case: mount with `lesson.content_blocks = []`; assert `markLessonOpened` → `onlessonopen` → `markLessonComplete` → `onlessoncomplete` fire in that order with no engage event in between. (FR-P15 zero-block edge case.)
- [x] Bump version to v0.54.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] `CHANGELOG.md` — v0.54.0 under "Added" (real-DOM lesson-render-pipeline test coverage: TextBlock observer callback path, VideoBlock URL-change + fallback wiring, LessonView lifecycle event firing).
- [x] Verify: `pyve test`, `pyve test tests/test_smoke_sveltekit.py`, `pnpm test`, `pnpm e2e`, `ruff`, `mypy`. The new tests should all pass on first run; any failure indicates a real bug uncovered by the tighter coverage (treat as a fix-before-merge, not a test-tuning exercise).

**Out of scope:**

- Replacing `createViewportTracker` and `createBlockTracker` helper tests entirely. Those tests are fast, debug-friendly, and document the timer/debounce contracts in isolation — keep them as a layered defence below the new mount tests.
- Real Chromium-driven `IntersectionObserver` testing (e.g. via `@vitest/browser`). The stubbed-observer + drive-the-callback pattern is sufficient at the unit-test layer; the e2e harness covers the real-browser version.
- Mounting `ContentBlock.svelte` directly. It's a thin dispatcher with no logic of its own; testing it adds no coverage that the per-block tests don't already give.
- Per-block lifecycle events at the `ContentBlock` level. Story I.p explicitly out-of-scoped this; revisit when a subscriber appears.

---

### Story I.u: v0.55.0 — Backfill Sidebar / Dashboard / Button Real-DOM Tests [Done]

Companion to Story I.t. Where I.t targets the lesson-render pipeline (high regression risk), this one targets the navigation / dashboard / button chrome. The existing helper-style tests cover the decision logic correctly but cannot catch markup, ARIA, or click-wiring bugs. This story adds parallel real-mount tests for `ModuleList`, `LessonList`, `Navigation`, `ProgressDashboard`, and `ResetCourseButton`.

The combined surface is wider than I.t but lower-risk. None of these components has hit a production regression in recent history; the value here is closing the long tail of "the test passes, but the rendered DOM doesn't match what the user sees" gaps.

**Tasks:**

- [x] `sveltekit_template/src/lib/components/ModuleList.test.ts` (new — `module-list.test.ts` keeps its helper coverage):
  - [x] Mount `<ModuleList>` with two modules (one locked) and assert: locked module renders a Lucide `<svg>` Lock icon next to the title, expanded panel (`<LessonList>`) is NOT in the DOM for the locked module even after a click on its header, unlocked module renders without the Lock icon and expands its `<LessonList>` on click.
  - [x] Mount with the active module highlighted; assert `border-l-blue-500 bg-blue-50` classes are present on the active `<li>` only.
- [x] `sveltekit_template/src/lib/components/LessonList.test.ts` (new):
  - [x] Mount with a mix of statuses (`not_started`, `in_progress`, `complete`, `optional`, `opened`); assert each row's status `<span>` text matches `○`/`…`/`✓`/`◇`/`…` respectively.
  - [x] Mount with one locked lesson; assert the locked row carries `aria-disabled="true"` and `cursor-not-allowed`; click the locked row and assert `goto` was NOT called.
  - [x] Mount with no locked lessons; click a row; assert `goto` was called with `/${moduleId}/${lessonId}`.
- [x] `sveltekit_template/src/lib/components/Navigation.test.ts` (extend — the helper cases stay): _added in-place to `navigation.test.ts` (lowercase) since macOS treats the two filenames as identical; helper `describe` blocks at the top, mount `describe` blocks below._
  - [x] Mount `<Navigation>` with `disabled={true}`; assert the Next/Finish button has the native `disabled` attribute and the `opacity-50 cursor-not-allowed` classes.
  - [x] Mount with `disabled={false}` and a non-null `nextLesson` store value; click the button; assert `goto` was called with the expected path string and `currentPosition.set(null)` was NOT called.
  - [x] Mount with `nextLesson` null (Finish state); click; assert `currentPosition.set(null)` was called BEFORE `goto('/')` (FR-P14 ordering — verify via mock call order).
- [x] `sveltekit_template/src/lib/components/ProgressDashboard.test.ts` (extend):
  - [x] Mount with three modules and partial progress; assert each module card renders the `<ProgressBar>` with the expected percent (parse the inline `style="width: …%"` attribute).
  - [x] Mount with `totalLessons = 0`; assert the curriculum-level summary bar is NOT rendered (the existing helper test covers the math; this test confirms the `{#if totalLessons > 0}` gate).
  - [x] Mount with one module fully complete and one not; assert the complete module renders "✓ Complete" and the incomplete module renders the "Start module →" / "Continue →" button.
- [x] `sveltekit_template/src/lib/components/ResetCourseButton.test.ts` (rewrite — the inline-handler-copy stays as documentation but the assertions now run against a real mount):
  - [x] Mount `<ResetCourseButton disabled={true}>`; assert the rendered `<button>` has `disabled` attribute and `cursor-not-allowed text-gray-300`; programmatic `.click()` does not invoke the handler (verify via mocked `resetProgress` having zero calls).
  - [x] Mount with `disabled={false}` and `confirmFn={() => false}`; click; assert `resetProgress` was NOT called.
  - [x] Mount with `disabled={false}` and `confirmFn={() => true}`; click; assert `resetProgress`, `currentPosition.set(null)`, `invalidateProgress`, and `goto('/')` all ran in that order.
- [x] Mirror to `src/learningfoundry/sveltekit_template/` (same Story I.r dependency note as I.s). _N/A — the workspace-root duplicate was deleted in Story I.s (v0.53.0); `src/learningfoundry/sveltekit_template/` is now the single source of truth, so no mirror step is required. Task kept marked done for accounting._
- [x] Bump version to v0.55.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] `CHANGELOG.md` — v0.55.0 under "Added" (real-DOM sidebar / dashboard / button test coverage).
- [x] Verify: `pyve test`, `pyve test tests/test_smoke_sveltekit.py`, `pnpm test`, `pnpm e2e`, `ruff`, `mypy`.

**Out of scope:**

- Replacing the existing helper tests (`module-list.test.ts`, `navigation.test.ts`, the `curriculumTotals` ProgressDashboard cases). They stay alongside the new mount tests — pure logic remains the fastest debugging surface.
- Visual regression / screenshot testing. Out of scope from I.q; remains so.
- Mounting `+layout.svelte` itself. The layout's logic is already covered by `layout.test.ts`'s helper tests + `layout.scroll.test.ts`'s targeted unit tests + the e2e harness. No additional mount-based assertion improves on what those three layers already check.
- Mounting route components (`+page.svelte`, `[module]/[lesson]/+page.svelte`). Routing-driven mounts belong in the e2e layer where SvelteKit's own machinery is in play.
- Cross-component integration tests (mount a sidebar with a real lesson view alongside it). Component-level mount + e2e is the right two-tier split; integration in the middle is duplicative.

---

### Story I.v: v0.56.0 — Fix Intermittent Event-Tracking Loss from 'getDb()' Init Race [Done]

The user reported that event tracking fails on roughly 50% of deployments — events appear to be written via `markLessonOpened` and the other `progress.ts` mutators, but later reads come back empty. The pattern is non-deterministic; it survived the existing test suite untouched.

Root cause is in [src/learningfoundry/sveltekit_template/src/lib/db/database.ts](src/learningfoundry/sveltekit_template/src/lib/db/database.ts) — `getDb()` is a textbook double-checked-async-init bug:

```ts
if (_db) return _db;
_SQL = await initSqlJs();        // ← await yields; concurrent callers all reach here
const saved = await loadFromIdb();
_db = saved ? new _SQL.Database(saved) : new _SQL.Database();
```

On first page load, multiple call sites hit `getDb()` in parallel (curriculum hydrate in the layout, `invalidateProgress` from the layout `$effect`, `markLessonOpened` from `LessonView`). All callers pass the `if (_db)` gate before any of them finishes the awaits; each constructs its own sql.js `Database` instance; only the *last* assignment to `_db` survives, and `persistDb()` only ever exports that one. Writes against instances that won the early race but lost the assignment race are silently dropped — they never reach IDB and never read back. Whether you observe the bug depends on microtask scheduling order, which varies by browser, deployment build, and warm-cache state — hence the ~50% rate.

`initSqlJs()` had the same shape and the same bug invisibly: `_SQL` was checked but never assigned inside the function (only in `getDb`'s outer scope), so concurrent callers each re-invoked the sql.js factory.

**Why tests missed it.** Existing tests in [progress.test.ts](src/learningfoundry/sveltekit_template/src/lib/db/progress.test.ts) and [LessonView.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/LessonView.test.ts) mock `database.js` entirely — they exercise the SQL contract but never the real `getDb()` lifecycle. There was no test that fired multiple `getDb()` calls concurrently and asserted single-instance behavior, no test that wrote through one reference and read back through another. This story closes both gaps.

**Fix shape.** Memoize the init promise in both `getDb()` and `initSqlJs()` so concurrent callers share the single in-flight initialization. The singleton architecture (module-scoped `_db`, `_SQL`) stays in place — promoting it to an injectable `ProgressRepo` class with explicit user-id partitioning is deferred to a follow-up so this fix stays surgical and reviewable.

**Tasks:**

- [x] `src/learningfoundry/sveltekit_template/src/lib/db/database.ts` — add `_dbInitPromise` and `_sqlInitPromise` module-scoped variables. Wrap the body of `getDb()` in a memoized `(async () => { ... })()` so the init runs at most once across concurrent callers; assign `_db` inside the IIFE so the synchronous fast path stays warm. Same pattern in `initSqlJs()` for `_SQL`.
- [x] `src/learningfoundry/sveltekit_template/src/lib/db/database.test.ts` (new) — two integration tests against the real sql.js (with `fake-indexeddb` providing IDB and a `globalThis.fetch` stub serving `static/sql-wasm.wasm` from disk):
  - [x] 5 concurrent `getDb()` calls return references that are `===` (single-instance invariant).
  - [x] A write through one reference is visible via every reference (the user-reported symptom: "events written but state isn't retrieved" — this is the test that would have caught the bug).
- [x] `src/learningfoundry/sveltekit_template/package.json` — add `fake-indexeddb` as a `devDependency` (^6.2.5). It's the standard tool for IDB in vitest+jsdom, and there's no other dep that gives us a working IDB in the test environment.
- [x] `src/learningfoundry/sveltekit_template/vite.config.ts` — under the `test` block, add `deps: { optimizer: { web: { exclude: ['sql.js'] } } }`. Without this, vite's pre-bundler eagerly evaluates sql.js's browser build at test startup, which fires the WASM fetch as a module-level side effect and produces an unhandled rejection in jsdom. Excluding defers sql.js evaluation until a test imports it (where the `fetch` stub in `database.test.ts` is already installed).
- [x] Bump version to v0.56.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] `CHANGELOG.md` — v0.56.0 under "Fixed" (intermittent progress data loss caused by race in `getDb()` / `initSqlJs()` singleton init; concurrent first-load callers each constructed their own sql.js `Database`, silently dropping writes to all-but-one instance) and "Added" (`fake-indexeddb` dev dep + `database.test.ts` real-DOM concurrency tests; `vite.config.ts` `sql.js` optimizer exclusion).
- [x] Verify: `pyve test` (255 pass), `pyve test tests/test_smoke_sveltekit.py` (12 pass, 1 skip), `pnpm test` (156 pass — was 154 before this story; +2 from `database.test.ts`), `ruff` (clean), `mypy` (clean, 17 files). `pnpm e2e` has 3 pre-existing failures on `main` at v0.55.0 (`navigation.spec.ts:10` sidebar lesson click, `navigation.spec.ts:24` dashboard "Start module" deep-link, `video.spec.ts:12` YouTube iframe count) — verified by stashing this story's changes and re-running on clean v0.55.0; same 3 fail. The failures are unrelated to the init race (vite production builds don't apply the test-only `optimizeDeps` config), and addressing them is deferred to a separate story.

**Out of scope (deferred to follow-up stories):**

- `ProgressRepo` class wrapping `progress.ts` with an injected `Database` — deferred to Story I.w. The seam already exists implicitly (no Svelte component imports `getDb` directly — only `progress.ts` does); promoting it to an explicit class lets tests construct fresh instances rather than sharing the module singleton, and prevents a future regression of this same class of bug.
- Introducing a `userId` (UUID v4 in `localStorage`) as a partition key for progress data, with a Web-Lock-protected bootstrap so the very-first-visit two-tab race doesn't generate two competing UUIDs — deferred to Story I.x (layered on top of I.w's class refactor). Pre-auth scaffolding; when auth lands the swap from local UUID to auth-issued ID is a key-rename rather than a schema migration.

**Out of scope (deferred indefinitely):**

- Cross-tab anti-clobber via Web Locks + reload-on-write. Latent issue (the whole-DB-blob persistence pattern is last-writer-wins across tabs of the same browser, for the same user) but distinct from the single-tab init race fixed here. Revisit when there's evidence of multi-tab learner workflows or when analytics/sync work makes the data model forced.
- Replacing sql.js + whole-DB-blob persistence with Dexie / per-row IDB. Considered and rejected: planned quiz-score analytics (averages, aggregates) want SQL ergonomics, and Dexie would push those reductions into hand-rolled JS. The bug fixed here is not caused by sql.js; it's caused by the singleton init pattern.

---

### Story I.w: v0.57.0 — 'Database' and 'ProgressRepo' Classes (Shape Refactor) [Done]

Story I.v fixed the immediate `getDb()` init race with a memoised init promise, but the underlying architecture — module-scoped mutable singletons (`_db`, `_SQL`) accessed implicitly by everything that imports `database.ts` — is what made the bug possible and what makes the *next* such bug invisible to the test suite. This story closes that category by promoting the implicit seam to an explicit class API.

This is a **pure shape change**: same DB, same SQL, same persistence behaviour, same singleton-per-page-load semantics. The win is testability (tests construct fresh class instances rather than sharing module-level state) and dependency clarity (anything that needs progress data takes a `ProgressRepo` rather than reaching into a module global).

Per-user partitioning, `userId`, the bootstrap Web Lock, and the legacy-`db`-key migration are explicitly deferred to Story I.x — they are a behavioural change layered on top of this shape change, and splitting them keeps each story reviewable and revertable.

**Architectural goals:**

1. **No module-scoped mutable singletons in `database.ts` / `progress.ts`.** Replace `let _db` / `let _SQL` with a `Database` class instance. `progress.ts` becomes a `ProgressRepo` class taking a `Database` in its constructor. Both held as singleton instances exported from `db/index.ts`.
2. **`getDb` / `persistDb` become private to `Database`, and the function-style exports from `progress.ts` are deleted in the same diff.** Per project guide ("don't use backwards-compatibility shims when you can just change the code"), all external callers migrate to the class API atomically in this story. No deprecated re-exports. **Actual caller set turned out to be 4 files, not the 5 the planning bullet listed:** `lib/stores/progress.ts`, `lib/components/LessonView.svelte`, `lib/components/ResetCourseButton.svelte`, `lib/components/QuizBlock.svelte`. The last one was missed in the planning grep — caught when `pnpm build` failed during smoke verification because `vi.mock` had masked it at the test layer. `lib/utils/progress.ts` and `lib/components/progress-dashboard.helpers.ts` matched a docstring/comment substring in the planning grep but neither actually imports from `$lib/db`.
3. **`Database` constructor takes no parameters in this story.** The IDB key stays `'db'`; persistence behaviour is unchanged. The constructor exists as a DI-shaped seam; `userId` joins it in I.x.

**Constraint — SQL contracts stay locked.** The INSERT / UPDATE / SELECT strings (especially the upgrade-only `ON CONFLICT DO UPDATE SET status = CASE WHEN ...` clause from Story I.p) are pinned by `progress.test.ts` as a regression net for schema/CASE semantics. Method bodies move into a class but the SQL inside them does not change. If a method's signature can be cleaner inside the class shape, change it; if the SQL needs changing, that's a separate concern in a different story.

**Tasks:**

- [x] `src/learningfoundry/sveltekit_template/src/lib/db/database.ts` — refactored module state into a `Database` class. Constructor `constructor()` (no params; `userId` joins in I.x). Instance state `#db`, `#SQL`, `#dbInitPromise`, `#sqlInitPromise` (all private, replacing the four module-scoped `let`s). Methods `getDb()`, `persist()`. The I.v memoisation pattern is preserved on the instance state. `reset()` was dropped from the planning bullet — no caller exists today and adding it would violate "don't add features beyond what the task requires". Module-level `getDb` / `persistDb` exports deleted.
- [x] `src/learningfoundry/sveltekit_template/src/lib/db/progress.ts` — promoted to a `ProgressRepo` class with constructor taking a `Database` instance. Methods carry the existing function bodies — `markLessonComplete`, `markLessonOpened`, `markLessonInProgress`, `getModuleProgress`, `getLessonProgress`, `getQuizScore`, `saveQuizScore`, `updateExerciseStatus`, `resetProgress`. (Method names match the existing function names — the planning bullet listed `recordQuizScore` / `setExerciseStatus` / `getExerciseStatus` from memory; reality is `saveQuizScore` / `updateExerciseStatus`, and `getExerciseStatus` doesn't exist.) SQL strings unchanged. Module-level function exports deleted.
- [x] `src/learningfoundry/sveltekit_template/src/lib/db/index.ts` — instantiates and exports `database` and `progressRepo` singletons plus the `Database` / `ProgressRepo` classes themselves.
- [x] **Migrated the 4 external callers** from function-style imports to the class API. SQL behaviour unchanged at every call site; only the import shape differs.
  - [x] `src/learningfoundry/sveltekit_template/src/lib/stores/progress.ts` — `progressRepo.getModuleProgress(...)`.
  - [x] `src/learningfoundry/sveltekit_template/src/lib/components/LessonView.svelte` — `markLessonOpened` / `markLessonInProgress` / `markLessonComplete` / `getLessonProgress` calls all `progressRepo.<method>(...)`.
  - [x] `src/learningfoundry/sveltekit_template/src/lib/components/ResetCourseButton.svelte` — `progressRepo.resetProgress()`.
  - [x] `src/learningfoundry/sveltekit_template/src/lib/components/QuizBlock.svelte` — `progressRepo.saveQuizScore(...)`. **(Not in original planning bullet — caught by the smoke test's `pnpm build` after `pnpm test` passed; `vi.mock('$lib/db/index.js')` masked the missing export at the test layer.)**
- [x] `src/learningfoundry/sveltekit_template/src/lib/db/database.test.ts` — extended I.v cases for the class API. New "independent instances" case asserts two `new Database()` references are `!==` and each holds its own internal sql.js Database. I.v concurrency cases preserved, now scoped to a single instance.
- [x] `src/learningfoundry/sveltekit_template/src/lib/db/progress.test.ts` — flipped from `vi.mock('./database.js')` to construction of a real `ProgressRepo` with a fake `Database` whose `getDb()` returns a stub. SQL-shape assertions identical. Three other test files (`stores/progress.test.ts`, `components/ResetCourseButton.test.ts`, `components/LessonView.test.ts`) had `vi.mock('$lib/db/index.js')` mocks of the function-style exports; updated each to mock the `progressRepo` shape. (Caught by `pnpm test`'s "No 'progressRepo' export is defined on the mock" errors after the first pass; not in the original planning bullet.)
- [x] Bumped version to v0.57.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] `CHANGELOG.md` — v0.57.0 under "Changed" (class refactor, callers migrated, no deprecated re-exports) and "Added" (independent-instances test).
- [x] Verify: `pyve test` (255 pass), `pyve test tests/test_smoke_sveltekit.py` (12 pass, 1 skip), `pnpm test` (157 pass — was 156 before this story; +1 from independent-instances case), `ruff` (clean), `mypy` (clean, 17 files). `pnpm e2e` retains I.v's 3 pre-existing failures (`navigation.spec.ts:10`, `navigation.spec.ts:24`, `video.spec.ts:12`) — not introduced by this story; same set as v0.55.0 / v0.56.0.

**Out of scope (deferred to Story I.x):**

- `userId` constructor parameter on `Database`, `localStorage` UUID v4 with `crypto.randomUUID()`, `navigator.locks`-protected bootstrap, per-user IDB key (`db:${userId}`), legacy-`db`-key one-shot migration, async `bootstrapDb()` setup in `+layout.svelte`. All deferred to keep this story a pure shape change with no behavioural delta.

**Out of scope (deferred indefinitely):**

- **Cross-tab anti-clobber.** Two tabs of the same browser can still last-writer-wins on the IDB blob — Web Locks + reload-on-write or BroadcastChannel-based leader election would solve it. Latent issue, distinct from this story; revisit when multi-tab learner workflows or sync work make it forced.
- **Replacing sql.js with Dexie or per-row IDB.** Same rejection as I.v: quiz analytics want SQL.
- **SQL contract changes** (INSERT / UPDATE / SELECT strings, the upgrade-only conflict CASE clause). Pinned by `progress.test.ts` as a regression net; any change is a separate concern.

---

### Story I.x: v0.58.0 — Per-User Data Partitioning + Web-Lock Bootstrap [Done]

Story I.w landed the class-shape refactor (`Database`, `ProgressRepo`) but the IDB key was still hardcoded `'db'` — single-tenant. This story adds the `userId` partition that makes the data model "this learner's progress" rather than "this browser's progress."

`userId` is a UUID v4 stored in `localStorage` (origin-scoped, so two tabs of the same browser converge on the same value once written). The very-first-visit two-tab race — where neither tab has written the UUID yet — is solved by wrapping the read-or-create in `navigator.locks.request('lf-user-id-bootstrap', ...)` so concurrent bootstraps converge on a single UUID.

When authentication eventually lands, the swap is a key-rename rather than a schema migration: replace the `localStorage` UUID with the auth-issued user ID and rename the IDB key once.

**Architectural goals:**

1. **`Database` constructor takes optional `userId?: string`.** IDB key becomes `db:${userId}`. Multiple instances with different IDs can coexist (tests pass an explicit userId for partition isolation; production omits it and the class lazy-resolves on first method call).
2. **One-shot legacy migration.** Pre-v0.58.0 progress lives under `IDB_KEY = 'db'`. On first init for any userId: if `db` exists, copy its bytes to `db:${userId}` (only if the per-user record doesn't already exist) and delete `db`. Idempotent — second call is a no-op. Claims existing pre-upgrade progress for whichever local UUID is generated on first post-upgrade load.
3. **Bootstrap is async and Web-Lock-protected.** `getUserId()` reads `localStorage` on the fast path and falls into a Web Lock if a write is needed.

**Bootstrap-shape decision (taken during implementation, documented in the CHANGELOG):** the lazy-self-bootstrap-inside-the-class shape, NOT an explicit `bootstrapDb()` ceremony. Rationale: the I.w call sites already await `progressRepo.<method>()`, so the userId resolution rides along on the existing async path with zero call-site churn. No `bootstrapDb()` function in `db/index.ts`; no `+layout.svelte` change. Trade-off: first method call pays the bootstrap cost (localStorage read + legacy migration check) — same cost the old singleton paid on first `getDb()`, so no regression.

**Tasks:**

- [x] `src/learningfoundry/sveltekit_template/src/lib/db/user-id.ts` (new) — `getUserId(): Promise<string>` with fast-path read from `localStorage` and slow-path write wrapped in `navigator.locks.request('lf-user-id-bootstrap', { mode: 'exclusive' }, ...)`. Fallback to unlocked generate-and-store on browsers without Web Locks (Safari < 15.4). Exports `_resetForTesting()` for tests.
- [x] `src/learningfoundry/sveltekit_template/src/lib/db/database.ts` — extended the I.w `Database` class:
  - [x] Constructor signature `constructor(userId?: string)`. Optional, since the class lazy-resolves via `getUserId()` if omitted.
  - [x] Private `#ensureUserId()` helper memoises the resolution promise so concurrent method calls share one userId fetch.
  - [x] `IDB_KEY` derivation moved into `#loadFromIdb(userId)` / `#saveToIdb(userId, data)` (instead of a module-level constant) so the per-user key is recomputed from the resolved userId.
  - [x] `#migrateLegacyKey(userId)` called once during `getDb()` first init: if IDB key `db` exists, `put` its bytes under `db:${userId}` (only when the per-user key doesn't already exist) and `delete` `db`. Idempotent.
- [x] `src/learningfoundry/sveltekit_template/src/lib/db/index.ts` — **unchanged from I.w.** The lazy-self-bootstrap shape means the existing `new Database()` / `new ProgressRepo(database)` singleton instantiation continues to work; no async `bootstrapDb()` function was introduced. (The story's planning bullet allowed either shape; this is the one chosen.)
- [x] `src/learningfoundry/sveltekit_template/src/routes/+layout.svelte` — **unchanged.** No mount-time bootstrap call needed; the first `invalidateProgress` triggers the lazy bootstrap inside `Database.getDb()`.
- [x] `src/learningfoundry/sveltekit_template/src/lib/db/database.test.ts` — extended with userId / partition cases:
  - [x] Construct two `new Database(userId)` instances with different `userId` values; assert each writes under its own IDB key (verified via raw IDB get of `db:user-a` / `db:user-b`); writes through one are not visible through the other (partition isolation).
  - [x] Migration test: pre-write a real `Uint8Array` (a sql.js export carrying a row) under the legacy `db` key in fake-indexeddb; instantiate `new Database('user-x')`; assert the migrated row reads back via the new instance, the legacy `db` key has been deleted, and the per-user `db:user-x` key now holds the bytes.
  - [x] Idempotency test: second `getDb()` call on the same instance does not re-migrate or fail.
  - [x] Two existing I.v concurrency cases (single-instance `getDb()` identity + write-visibility) preserved with explicit userId arg.
- [x] `src/learningfoundry/sveltekit_template/src/lib/db/user-id.test.ts` (new):
  - [x] Fresh `localStorage` → `getUserId()` returns a UUID v4-shaped string and persists it.
  - [x] Pre-populated `localStorage` → `getUserId()` returns the existing value (no rotation).
  - [x] Two parallel `getUserId()` calls on a fresh `localStorage` return the *same* UUID via a `vi.stubGlobal('navigator', { locks: ... })` shim that simulates real exclusive serialisation (queue + drain). Lock-fallback path covered implicitly by the no-stub branch in production code.
- [x] `docs/specs/project-essentials.md` — added a new "In-browser progress DB is per-user-partitioned" bullet under Architecture Quirks documenting the IDB key, localStorage key, bootstrap shape, auth-migration plan, and the still-open cross-tab anti-clobber caveat.
- [x] Bumped version to v0.58.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] `CHANGELOG.md` — v0.58.0 under "Added" (per-user partition; user-id.ts with Web-Lock bootstrap; legacy-key migration; partition / bootstrap / migration tests) and "Changed" (`Database` constructor gains optional `userId?: string`; bootstrap-shape decision documented).
- [x] Verify: `pyve test` (255 pass), `pyve test tests/test_smoke_sveltekit.py` (12 pass, 1 skip), `pnpm test` (163 pass — was 157 before this story; +6 from new I.x tests: 3 in user-id.test.ts, 3 in database.test.ts), `ruff` (clean), `mypy` (clean, 17 files). `pnpm e2e` retains the 3 pre-existing failures from v0.55.0 / v0.56.0 / v0.57.0; not introduced by this story.

**Implementation notes / surprises:**

- vitest's jsdom environment exposes `globalThis.localStorage` as a Proxy that rejects method-property writes (it only accepts string-string property assignments to mimic Storage's `localStorage.foo = 'bar'` index access). Both `database.test.ts` and `user-id.test.ts` install a Map-backed `fakeStorage` via `Object.defineProperty(globalThis, 'localStorage', ...)` in `beforeAll` to substitute. Took two failed attempts (`Object.assign` rejected by the proxy; `removeItem` undefined) before landing on the full-replacement pattern.

**Out of scope (deferred indefinitely):**

- **Cross-tab anti-clobber for the same `userId`.** Two tabs of the same browser, same user, can still last-writer-wins on the IDB blob — Web Locks + reload-on-write or BroadcastChannel-based leader election would solve it. Latent issue, distinct from this story; revisit when multi-tab learner workflows or sync work make it forced.
- **Multi-account UI.** No surfaced UX exposing the `userId` or letting the learner pick / switch accounts. The class architecture (post-I.w) supports it, but plumbing it into the UI without an auth concept is out of scope.
- **Replacing sql.js with Dexie or per-row IDB.** Same rejection as I.v: quiz analytics want SQL.

---

### Story I.y: v0.59.0 — Sidebar Collapse + Highlight Drop on Course-Title Click [Done]

**Bug report:** "Clicking on the course title link on the left sidebar should collapse and deactivate the active module. An expanded module and highlighted lesson should be the indicator of what is in the content pane and when that dashboard is in the content pane, that is confusing."

The course-title link in [src/routes/+layout.svelte](src/learningfoundry/sveltekit_template/src/routes/+layout.svelte) was a bare `<a href="/">` with no click handler. Navigating from a lesson page to `/` (the dashboard) left `currentPosition` populated, so:
1. `ModuleList`'s active-highlight CSS (`mod.id === $currentPosition?.moduleId`) kept the lesson's parent module visually marked active.
2. The auto-expand `$effect` saw no change in `$currentPosition.moduleId` and didn't fire a collapse.

The cascade was already in place — `ResetCourseButton` and the FR-P14 Finish button both clear `currentPosition` for exactly this reason, and `computeAutoExpand(null, lastAutoExpandedModuleId !== null)` already returns the collapse instruction (Story I.n test at `layout.test.ts:67-72`). The bug was that the title link never triggered the clear.

**Fix shape.** New `clearActivePosition()` helper in `src/routes/layout.helpers.ts` (one line: `currentPosition.set(null)`). The title link's `onclick` calls it. Same pattern `ResetCourseButton` and `Navigation` (Finish) already use.

**Why a helper rather than inlining.** The inline form is also one line, but the helper makes the behaviour testable at the unit layer without mounting the full layout (the latter is explicitly out-of-scope per Story I.u). It also names the operation, which is useful documentation.

**Why this wasn't caught earlier.** No real-DOM mount test of `+layout.svelte` exists (Story I.u explicitly out-of-scoped layout mounts as redundant with the helper-style coverage + e2e). The bug is the kind that helper-style tests structurally can't catch: it's a wiring bug ("the link is missing a handler"), not a logic bug. The 3 pre-existing e2e failures noted in Story I.v probably *would* have caught this if the e2e suite were green; that's a separate concern tracked for a future story.

**Tasks:**

- [x] `src/learningfoundry/sveltekit_template/src/routes/layout.helpers.ts` (new) — `clearActivePosition()` that calls `currentPosition.set(null)`. Docstring names the cascade through `ModuleList`'s `$effect` + the active-highlight CSS, and references the existing `ResetCourseButton` / `Navigation` (FR-P14) precedents.
- [x] `src/learningfoundry/sveltekit_template/src/routes/+layout.svelte` — import `clearActivePosition` from `./layout.helpers.js`; wire `onclick={clearActivePosition}` on the course-title `<a>`. The browser's default link navigation still fires (no `event.preventDefault()`), so SvelteKit's client-side router takes over from there as before.
- [x] `src/learningfoundry/sveltekit_template/src/routes/layout.test.ts` — added a "Bug 4 — sidebar collapse on home nav" describe block with two cases: clearing a populated `currentPosition` resets it to null; calling on an already-null position is a no-op. Imports the real `currentPosition` writable from `$lib/stores/curriculum.js` so the test exercises the actual store interaction.
- [x] Bump version to v0.59.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] `CHANGELOG.md` — v0.59.0 under "Fixed" (sidebar still showing expanded module + highlighted lesson when learner navigates to dashboard via course-title link; the active-position cascade was already plumbed but the title link was never wired to trigger it).
- [x] Verify: `pyve test`, `pyve test tests/test_smoke_sveltekit.py`, `pnpm test`, `ruff`, `mypy`. `pnpm e2e` retains the 3 pre-existing failures from earlier stories.

**Out of scope:**

- **Real-DOM mount test of `+layout.svelte` for the title-link click.** Helper-level coverage matches the codebase's established pattern (Story I.u). The wiring (layout's `onclick={clearActivePosition}`) is type-checked at compile time and exercised by e2e. Adding a layout mount test for one click event would re-litigate Story I.u's out-of-scope decision; defer it until either (a) e2e fails to catch a similar wiring bug or (b) a separate story revisits the layout's test surface.
- **Fixing the 3 pre-existing e2e failures** noted in Story I.v. Investigating why `navigation.spec.ts:10`, `navigation.spec.ts:24`, and `video.spec.ts:12` fail on clean `main` is its own problem; not blocked by this story and shouldn't ride along.
- **Sidebar redesign / dashboard-state semantics.** The user's framing ("an expanded module and highlighted lesson should be the indicator of what is in the content pane") is satisfied by this story's fix. Any broader rethink of how the sidebar communicates "where you are" belongs in a separate design exploration.

---

### Story I.z: v0.60.0 — Investigate and Fix the 3 Pre-Existing E2E Failures [Done]

Stories I.v through I.y each documented that `pnpm e2e` retains 3 pre-existing failures on clean `main`, unrelated to the work in those stories. Verified at v0.56.0 by stashing the in-flight changes and re-running on clean v0.55.0; same 3 fail. They have presumably been broken for some time without anyone treating it as a blocker.

The failing tests:

1. [`e2e/navigation.spec.ts:10`](src/learningfoundry/sveltekit_template/e2e/navigation.spec.ts#L10) — "sidebar lesson click updates URL". FR-P9 regression coverage; predates v0.46.0. Times out on `aside nav button` selector before any assertion runs.
2. [`e2e/navigation.spec.ts:24`](src/learningfoundry/sveltekit_template/e2e/navigation.spec.ts#L24) — `dashboard "Start module" deep-links into a lesson`. Times out on `getByRole('button', { name: /start module|continue/i })`.
3. [`e2e/video.spec.ts:12`](src/learningfoundry/sveltekit_template/e2e/video.spec.ts#L12) — "lesson page renders at most one YouTube iframe per video block". FR-P10 regression coverage; depends on the same sidebar-click navigation as the first test, so probably fails for the same root cause.

All three fail early in the page-interaction phase rather than at the assertion. Two of three fail on the `aside nav button` selector specifically, which suggested one of: selector drift, curriculum loading failure, or a hydrate race.

**Root cause (confirmed via Playwright trace.zip page snapshots): curriculum loading failure.** The trace's DOM snapshot at the point of timeout showed `<paragraph>Loading…</paragraph>` in the sidebar (where `ModuleList` should have rendered `<nav>`) and `<paragraph>Loading curriculum…</paragraph>` in the main pane. The title link rendered the fallback string `"LearningFoundry"` rather than the curriculum's actual title — a clean tell that `$curriculum` stayed null.

The actual cause: **`static/curriculum.json` does not exist in the template** (the fixture lives at [e2e/fixtures/curriculum.json](src/learningfoundry/sveltekit_template/e2e/fixtures/curriculum.json) but was never copied into `static/` before `pnpm build`). `pnpm preview` therefore served a `build/` that 404'd on every `/curriculum.json` request, the curriculum readable's `loadCurriculum()` rejected, and `ModuleList`'s `{#if $modules.length && $curriculum}` gate stayed false. Three tests timed out on `aside nav button`; the rest passed because they exercised parts of the layout that render without the curriculum (e.g. the disabled Reset button).

The third specific test (`video.spec.ts:12`) failed for the same reason — it shares the `aside nav button` click prelude with the navigation tests, so the same root cause covers all three.

**False-start in the fix:** the first attempt added a Playwright `globalSetup` script that copied the fixture into `static/` before the suite ran. It didn't work because **Playwright runs `webServer` BEFORE `globalSetup`** — so `pnpm build` had already executed against an empty `static/` by the time the fixture arrived. Confirmed by adding a `console.log` to the setup: the copy log appeared, but `[404] GET /curriculum.json` continued in the WebServer logs. Fix moved the copy into the `webServer.command` itself, ahead of the build, where it is ordered correctly.

**Why this matters.** Without a green e2e suite, wiring bugs (the kind Story I.y called out as structurally uncatchable by this codebase's helper-style unit tests) have no automated regression net. Story I.y's fix would have been caught by `e2e/navigation.spec.ts:24` (clicking "Start module" on the dashboard, then asserting the sidebar collapses on home-link click) — except that test was already broken. The signal-to-noise on `pnpm e2e` is the real problem: a chronically-red suite trains everyone to ignore it.

**Tasks:**

- [x] Reproduced locally with `pnpm e2e` from the template — same 3 failures, confirmed deterministic (not flake).
- [x] Inspected `test-results/<spec>/error-context.md` page snapshots — every failure showed "Loading…" / "Loading curriculum…" and the fallback "LearningFoundry" title, confirming `$curriculum` was null.
- [x] Verified `static/` contents — only `sql-wasm.wasm` present, no `curriculum.json`. The build/ output therefore 404s on `/curriculum.json`.
- [x] Verified manually that running `cp e2e/fixtures/curriculum.json static/ && pnpm build` produces `build/curriculum.json`, so the SvelteKit static adapter does pick up files from `static/` correctly — the gap was just that the fixture wasn't there.
- [x] Wrote new [e2e/global-teardown.ts](src/learningfoundry/sveltekit_template/e2e/global-teardown.ts) that removes `static/curriculum.json` after the suite so the template's `static/` directory stays clean for `pnpm dev`.
- [x] Updated [playwright.config.ts](src/learningfoundry/sveltekit_template/playwright.config.ts):
  - [x] `webServer.command` now chains `cp e2e/fixtures/curriculum.json static/curriculum.json && pnpm build && pnpm preview ...` so the fixture is in place before the build, and the preview serves a build that includes it.
  - [x] `webServer.timeout` bumped from 60s to 120s to accommodate the build step in the chain.
  - [x] `globalTeardown: './e2e/global-teardown.ts'` registered.
  - [x] Inline comment explains the `webServer`-runs-before-`globalSetup` ordering pitfall so a future maintainer doesn't refactor the copy into globalSetup and re-introduce the bug.
- [x] Re-ran `pnpm e2e` to confirm: **14 passed, 0 failed** in 12.6s (was 11 passed / 3 failed in ~1.0 min on the broken state — the wall-clock improvement is the 30s-per-failure timeout that no longer happens).
- [x] Bumped version to v0.60.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] `CHANGELOG.md` — v0.60.0 under "Fixed" (3 pre-existing e2e failures rooted in the curriculum fixture never being planted before `pnpm build`).
- [x] Verify: `pyve test` (255 pass), `pyve test tests/test_smoke_sveltekit.py` (12 pass, 1 skip), `pnpm test` (165 pass), `pnpm e2e` (14 pass, 0 fail), `ruff` (clean), `mypy` (clean).

**Out of scope:**

- **General e2e refactor / hardening.** This story is "stop the bleeding on the 3 broken tests," not "rewrite the suite." Patterns like fixture management, page-object modeling, or migrating to `@vitest/browser` are separate concerns. If the investigation surfaces architectural issues, file follow-up stories rather than expanding this one.
- **Adding new e2e coverage** (e.g. for Story I.y's title-link clear behaviour, Story I.x's per-user partition, or Story I.w's class refactor wiring). Worth doing — but only after the existing suite is green so new failures aren't lost in the noise.
- **CI integration of `pnpm e2e`.** Right now there's no CI gate enforcing e2e green. Adding one before the suite is reliable would cause more pain than it solves; revisit after this story lands.
- **Investigating other pytest-side flakes.** `pyve test tests/test_smoke_sveltekit.py` skips one test; that's a separate concern with its own intentional `skipif` (presumed) and not in scope here.

---


### Story I.aa: v0.61.0 — Reliable '/sql-wasm.wasm' Provisioning + Typed DB-Init Failure [Done]

Recording broke silently on every `learningfoundry preview` run after the first. The CLI logged `[404] GET /sql-wasm.wasm`; the UI showed no progress checkmarks, no in-progress icons, no module/lesson advancement — every lesson event, quiz score, and exercise status write rejected at `Database.getDb()` and the rejection never surfaced to the learner.

**Root cause.** The wasm asset had no single owner. Two fragile channels were *both* expected to keep `output_dir/static/sql-wasm.wasm` populated, and they cancelled each other:

1. **Template copy via `_atomic_copy`.** The wasm source lives in [src/.../sveltekit_template/static/sql-wasm.wasm](src/learningfoundry/sveltekit_template/static/sql-wasm.wasm) but is gitignored ([.gitignore:36](.gitignore#L36)) — absent on clean checkouts and from the published wheel. Even when present locally, `static/sql-wasm.wasm` was *not* in `_PRESERVED_PATHS`, so every rebuild wiped any existing copy in `output_dir/static/`.
2. **`pnpm postinstall` hook in [package.json:13](src/learningfoundry/sveltekit_template/package.json#L13).** Copied `node_modules/sql.js/dist/sql-wasm.wasm` → `static/sql-wasm.wasm`, but only when `pnpm install` ran — and `pipeline.run_preview` skips install when `check_dep_state == UNCHANGED` (every iterate-on-content rebuild). Also flaky across pnpm version/configuration combinations that don't honour root-package lifecycle scripts.

The interaction: build N+1 wiped the wasm via channel 1 and skipped channel 2. The user's `learningfoundry-test/dist/` was reproducible evidence — `static/sql-wasm.wasm` missing, `node_modules/sql.js/dist/sql-wasm.wasm` present, `static/.gitkeep` mtime proving `_atomic_copy` had refreshed `static/` from the template (which only ships `.gitkeep`). The "works the first time then breaks" pattern matched exactly: the first preview installed deps and ran postinstall; every preview after didn't.

**Why this wasn't caught.** The pipeline test class `TestRunPreviewSkipsInstall` already verified that `pnpm install` is correctly *skipped* on `DepState.UNCHANGED` — but never checked the *consequence* (no wasm). The frontend `database.test.ts` shimmed `fetch` to serve wasm bytes from disk, accidentally masking the very failure mode that breaks production. E2E always ran fresh (so postinstall always ran), exercising only the path that worked. And `Database.getDb()` rejected with an opaque `Error` from sql.js's WebAssembly fetch path, indistinguishable to UI callers from "no progress yet" — so the CLI logs were the only signal, and they read like dev-server noise.

**Fix.** Single-owner the asset on the Python side, and make the DB-init failure typed and loud.

- [pipeline.py](src/learningfoundry/pipeline.py) — new `_ensure_sql_wasm(output_dir)` helper called unconditionally from `run_preview` after the install gate. Copies `output_dir/node_modules/sql.js/dist/sql-wasm.wasm` → `output_dir/static/sql-wasm.wasm` whenever destination is missing or content-stale (size-based check on a version-pinned dep is a strong proxy). Raises `GenerationError` with a clear message if the source is absent, converting a runtime 404 into a build-time error.
- [generator.py:34](src/learningfoundry/generator.py#L34) — `static/sql-wasm.wasm` added to `_PRESERVED_PATHS`. Belt-and-braces; `_ensure_sql_wasm` is the source of truth, but preserving an existing copy across `_atomic_copy` is cheap insurance.
- [package.json:13](src/learningfoundry/sveltekit_template/package.json#L13) — `postinstall` line removed. Two-ways-of-doing-the-same-thing was how this bug got nasty; the Python pipeline is now the single owner.
- [database.ts](src/learningfoundry/sveltekit_template/src/lib/db/database.ts) — exported new `WasmAssetMissingError` class. Inside `#initSqlJs`, a HEAD precheck against `/sql-wasm.wasm` runs *before* delegating to `initSqlJs` so a 404 surfaces as a typed error consumable by UI error boundaries — bypasses sql.js's module-level wasm caching, which previously masked 404s as silently rejected progress writes.

**Tasks:**

- [x] Wrote 6 failing tests covering each leaf of the bug:
  - [tests/test_generator.py](tests/test_generator.py): `test_static_sql_wasm_is_preserved_across_rebuilds` — synthesises a clean template (no wasm), seeds the file in output, asserts it survives `_atomic_copy`.
  - [tests/test_pipeline.py](tests/test_pipeline.py) `TestRunPreviewProvisionsWasm`: 3 tests covering `UNCHANGED` provisioning, `FIRST_BUILD` content match, and the loud-failure path when the source wasm is absent.
  - [database.test.ts](src/learningfoundry/sveltekit_template/src/lib/db/database.test.ts): 2 tests under `Database — wasm-asset failure surfaces as WasmAssetMissingError` covering the rejection-class invariant and the `assetUrl` diagnostic field.
- [x] Confirmed each test failed for the right reason before any fix code was written. The TS test failure was especially diagnostic: `getDb()` *resolved* on a 404 because sql.js's module-level state had cached the wasm from earlier-running tests in the same suite — confirming that relying on sql.js's own error path is unreliable and that the precheck is necessary.
- [x] Implemented `pipeline._ensure_sql_wasm`; wired into `run_preview` after the conditional install block.
- [x] Added `static/sql-wasm.wasm` to `generator._PRESERVED_PATHS`.
- [x] Removed `postinstall` from `package.json`.
- [x] Added `WasmAssetMissingError` class and HEAD-fetch precheck to `database.ts`; updated the file's module-level doc comment to reflect the new owner.
- [x] Updated 3 existing `TestRunPreviewSkipsInstall` tests to patch `_ensure_sql_wasm` (consistent with their pre-existing patches of `run_build` and `subprocess.run`).
- [x] Verified prevention scan: grep for `postinstall` / `require.resolve` / `fs.copyFileSync` / `node_modules.*dist` patterns elsewhere in the template — only the now-orphaned doc-comment reference and the test-file's bug-history comment matched. No other asset uses the broken pattern.
- [x] Verified prevention scan: all `Database.getDb()` callers go through `progress.ts` (`ProgressRepo` chokepoint from Story I.w). UI consumers `await` `progress.ts` methods, so a thrown `WasmAssetMissingError` propagates up there as a single integration point for the follow-up banner work.
- [x] `pyve test tests/` — 259 pass.
- [x] `pnpm test` — 167 pass (including the 2 new wasm-asset cases).
- [ ] **Housekeeping → Story I.bb:** UI surfacing of `WasmAssetMissingError`. The class is now thrown reliably; consumers in `progress.ts` need to either catch and re-throw with progress-write context, or let it propagate to a layout-level `<svelte:boundary>` that renders a recoverable banner ("Progress recording is paused — try refreshing"). Out of scope here because it's UI work separable from the asset-pipeline root-cause fix and benefits from a usability pass on copy/iconography.
- [ ] **Housekeeping → Story I.cc:** investigate whether the user's earlier pnpm-vs-npm wiring grief is rooted in the same lifecycle-script handling, now that we no longer depend on `postinstall`. If pnpm in their environment skips the *postinstall* of root packages, it may also skip other lifecycle scripts that future template work might add — a discovery story rather than a fix.
- [x] Bumped version to v0.61.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] `CHANGELOG.md` — v0.61.0 under "Fixed".
- [x] Verify: `pyve test tests/` (259 pass), `pnpm test` (167 pass).

**Out of scope:**

- **UI banner for `WasmAssetMissingError`.** Captured as deferred housekeeping above. The class and its propagation path exist; the UX work to render and recover from it is separate. → Story I.bb.
- **Investigation of pnpm lifecycle-script reliability.** The user's earlier "pnpm has wiring problems passing certain params; only npm worked" report may share a root with the now-removed `postinstall` flakiness. Worth a discovery pass before adding more lifecycle-dependent template scripts. → Story I.cc.
- **End-to-end test for the second-preview path.** The unit-level coverage in `tests/test_pipeline.py` exercises the exact gating + provisioning behaviour at the smallest scope; an e2e test that runs `learningfoundry preview` twice and checks recording would be valuable but adds infrastructure (process spawning, wasm pre-seeding under a clean output dir) for marginal additional confidence.
- **Auditing other gitignored-template-asset risks.** The prevention scan was scoped to assets shipped via `postinstall`. A broader audit ("what else in `sveltekit_template/static/` is gitignored or otherwise relies on a post-template-copy step?") would surface lurking variants of this bug class. Worth doing but not blocking on the recording fix.
- **CI integration to catch this regression.** The new pipeline tests cover the regression at the unit level; CI gate work belongs with the broader CI story (also deferred from I.z).

---

### Story I.aa.1: v0.62.0 — Sidebar Collapse on Course-Title Click from Dashboard [Done]

A sidebar regression orthogonal to Story I.y. **Repro:** on the dashboard (no lesson active, `currentPosition === null`), manually expand a module by clicking its header, then click the course title link. Pre-fix: the module remained expanded. Story I.y had only fixed the path where a lesson *was* active (`currentPosition` transitioning non-null → null collapses through the auto-expand `$effect`).

**Root cause.** [layout.helpers.ts](src/learningfoundry/sveltekit_template/src/routes/layout.helpers.ts) `clearActivePosition` set `currentPosition` to null. ModuleList's auto-expand `$effect` was supposed to observe that change and collapse. But Svelte 5's `$store` deref maintains an internal `$state` for the store and updates it via `Object.is`-equality — so a `set(null)` on an already-null `currentPosition` produces no change to the dependent effect, and the effect never re-runs. The course-title-click reset path simply did not fire when the learner started from the dashboard.

A first attempt extended `computeAutoExpand` to also reason about a `expandedModuleId` argument so the helper could distinguish "manually expanded" from "auto-expanded" inputs. That change passed its helper-level unit test but failed the component-level mount test for exactly the reason above: the helper was never invoked because the `$effect` never re-ran. The hypothesis was wrong, and the fix had to be a level higher up the stack.

**Why this wasn't caught by Story I.y's review.** Story I.y added two regression cases in [layout.test.ts](src/learningfoundry/sveltekit_template/src/routes/layout.test.ts): `populated → null` and `null → null`. The `null → null` case asserted that `clearActivePosition` *was called*; it didn't assert anything about the resulting sidebar state because that test scope (the layout helpers, not ModuleList) couldn't observe component-local state. Same anti-pattern flagged in Story I.aa: a test guarded the gating behaviour but not the consequence.

**Fix.** Lift `expandedModuleId` from `ModuleList`'s component-local `$state` to a module-level `writable` in [stores/curriculum.ts](src/learningfoundry/sveltekit_template/src/lib/stores/curriculum.ts), so external callers can collapse modules directly without going through the `$effect`. `clearActivePosition` now resets two stores: `currentPosition` (for the active-lesson highlight, unchanged from Story I.y) and `expandedModuleId` (new). The auto-expand `$effect` keeps its original 2-arg `computeAutoExpand` signature and continues to handle the auto-expand-on-navigation and FR-P14 Finish paths; it just stops being a side-channel for the course-title-click case. `lastAutoExpandedModuleId` stays component-local — it's pure auto-expand bookkeeping for Story I.f manual-toggle preservation, with no external consumer.

**Tasks:**

- [x] Wrote failing tests at two scopes:
  - Helper-level (in [module-list.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/module-list.test.ts)) for the first hypothesis (extend `computeAutoExpand`); these were *removed* when the hypothesis was revised because the helper signature is unchanged in the final fix.
  - Component-level real-DOM mount (in [ModuleList.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/ModuleList.test.ts)): mount `ModuleList`, click a header to manually expand, call `clearActivePosition()`, assert the inner `<ul>` is gone. This test is what caught the wrong-hypothesis pivot and is the gate artefact for the fix.
  - Layout helper tests (in [layout.test.ts](src/learningfoundry/sveltekit_template/src/routes/layout.test.ts)): two new cases asserting `clearActivePosition` clears `expandedModuleId` both when `currentPosition` was non-null (I.y path) and when it was null (I.aa.1 path).
- [x] Confirmed each test failed for the right reason, then made each pass.
- [x] Lifted `expandedModuleId` to a `writable<string | null>` in [stores/curriculum.ts](src/learningfoundry/sveltekit_template/src/lib/stores/curriculum.ts).
- [x] Updated [ModuleList.svelte](src/learningfoundry/sveltekit_template/src/lib/components/ModuleList.svelte) to subscribe via `$expandedModuleId` and write via `expandedModuleId.set(...)`. Original `$effect` and `computeAutoExpand` signature restored — the lift sidesteps the `Object.is` short-circuit entirely.
- [x] Updated [layout.helpers.ts](src/learningfoundry/sveltekit_template/src/routes/layout.helpers.ts) `clearActivePosition` to reset both stores and re-documented the `Object.is` rationale inline so a future maintainer doesn't refactor the second `set(null)` away.
- [x] Reverted the failed `computeAutoExpand`-signature-extension from this story's first attempt (the helper file is byte-identical to its v0.61.0 state). Reverted the `untrack` import added during the same dead end.
- [x] Updated [ModuleList.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/ModuleList.test.ts) mock for `$lib/stores/curriculum.js` to (a) make the `currentPosition` mock notify subscribers on `set` (matching writable semantics, so the auto-expand $effect path is testable), and (b) export a real Svelte `writable` for `expandedModuleId` so `clearActivePosition`'s `.set(null)` actually drives the component.
- [x] Renamed Story I.y's "is a no-op when currentPosition is already null" test to "leaves currentPosition null when it was already null" — under I.aa.1, `clearActivePosition` is no longer a no-op in that case, it now also resets `expandedModuleId`.
- [x] Bumped version to v0.62.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] `CHANGELOG.md` — v0.62.0 under "Fixed" / "Changed".
- [x] Verify: `pyve test tests/` (259 pass), `pnpm test` (170 pass — was 167, +1 ModuleList real-DOM, +2 layout-helper anti-regression cases). `ruff check .` clean.

**Out of scope:**

- **Migrating other component-local state to stores.** The lift was specific to `expandedModuleId` because it has an external consumer (`clearActivePosition`). State that is purely component-internal (`lastAutoExpandedModuleId`, sidebar scroll position, etc.) stays local; lifting unnecessarily inverts dependencies and complicates testing.
- **Refactor of the auto-expand `$effect`'s ergonomics.** The effect now writes to two state shapes (a store and a `$state` rune); a future cleanup might unify them. Not blocking — current shape is clear if the comment is read.
- **Auditing Svelte 5 `$store` Object.is-equality elsewhere.** The same short-circuit may bite other "set null on already-null" patterns in the codebase. A broader sweep is worthwhile but separate; the only known case today is `currentPosition`.
- **End-to-end Playwright coverage.** The component-level real-DOM test exercises the exact wiring; an e2e click-the-title-link test would be valuable for visual confirmation but adds infrastructure for marginal additional confidence.

---

### Story I.aa.2: v0.62.1 — Strict Schema Validation + Lesson-Route Locking Failsafe [Done]

A user-visible reproduction of the locking feature being silently disabled. **Repro:** YAML curriculum has `sequential: true` written one indent level too high (directly under `curriculum:` instead of nested under `curriculum.locking:`). Pre-fix: every module is freely expandable, every lesson is freely openable, no lock icon appears in the sidebar — exactly as if locking were turned off.

**Root cause is two distinct gaps that compound.**

1. **Schema permissiveness.** [schema_v1.py](src/learningfoundry/schema_v1.py)'s Pydantic models defaulted to `extra='ignore'` (Pydantic v2's out-of-box default). The user's mis-placed `sequential: true` was an unknown field on `CurriculumDef` and was silently discarded; `LockingConfig` got its default `sequential=False`. There was no error, no warning, no log — the bug was indistinguishable from "feature disabled by config." Confirmed by parsing the user's actual `learningfoundry-test/curriculum.yml` and printing the resolved `static/curriculum.json`: `"locking": { "sequential": false, "lesson_sequential": false }` despite the YAML containing `sequential: true`.
2. **No locking guard at the lesson route.** [+page.svelte](src/learningfoundry/sveltekit_template/src/routes/[module]/[lesson]/+page.svelte) read `page.params` and rendered `<LessonView>` if the requested module/lesson existed in the curriculum. It did not consult `lockedModuleIds` / `lockedLessonIds`. Even if the schema gap were fixed, a learner who typed a locked-lesson URL, refreshed an old tab, or followed a stale bookmark would still bypass the sidebar's locking enforcement entirely. The sidebar-only policy was defense-in-one-place rather than defense-in-depth.

The user's third symptom — "no visual indicator for locked modules" — was a downstream consequence of (1), not a separate gap. The lock icon, gray-400 text, and `cursor-not-allowed` styling already existed in [ModuleList.svelte:79-86](src/learningfoundry/sveltekit_template/src/lib/components/ModuleList.svelte#L79-L86); they just never rendered because nothing was actually locked.

**Why this wasn't caught.** [test_schema_v1.py](tests/test_schema_v1.py) had thorough happy-path coverage but no tests for misplaced or typo'd fields — the schema's silent-drop behaviour was untested. [locking.test.ts](src/learningfoundry/sveltekit_template/src/lib/utils/locking.test.ts) thoroughly covered `isModuleLocked` / `isLessonLocked` *as helpers* but no integration test exercised "given a curriculum with sequential locking, does the lesson route refuse to render a locked lesson?" — the route had no test file at all. The test pyramid had two well-tested layers (schema parsing, locking math) and a wide-open gap between them where the actual user-visible behaviour lives. The same shape as Story I.aa: **happy-path coverage doesn't catch silent failure modes.**

**Fix — three pieces.**

1. **Strict schema.** New `StrictModel` base class in [schema_v1.py](src/learningfoundry/schema_v1.py) sets `model_config = ConfigDict(extra='forbid')`. Every curriculum-schema model (`CurriculumDef`, `Module`, `Lesson`, `LockingConfig`, `CurriculumV1`, all `*Block` types, `AssessmentRef`) now inherits from `StrictModel`. A misplaced field anywhere in the YAML produces a `ValidationError` of the form `curriculum.sequential — Extra inputs are not permitted [type=extra_forbidden, ...]`, with a JSON-pointer path to the offending field name. Verified against the user's actual YAML: the strict validator now rejects it with that exact message instead of silently producing a non-locking output.
2. **Lesson-route locking guard.** [+page.svelte](src/learningfoundry/sveltekit_template/src/routes/[module]/[lesson]/+page.svelte) now derives `isLocked` from the same `isModuleLocked` / `isLessonLocked` helpers the sidebar uses, and renders [LockedLessonPlaceholder.svelte](src/learningfoundry/sveltekit_template/src/lib/components/LockedLessonPlaceholder.svelte) (lock icon + module/lesson title + "Complete X to unlock this lesson" + Return-to-dashboard CTA) when the requested URL points at a locked lesson. The `navigateTo` side-effect in `onMount` / `$effect` is now guarded by `!isLocked` so a locked-URL load doesn't write `currentPosition` and therefore doesn't highlight the gated module in the sidebar.
3. **Visual indicator regression-guard.** No change to the existing styling — the gap was that locking never fired, not that the styling was wrong. New regression test in [ModuleList.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/ModuleList.test.ts) asserts the locked-button carries `cursor-not-allowed` and `text-gray-400` so a future refactor can't silently regress it.

**Tasks:**

- [x] Wrote 4 failing schema-strictness tests (`test_sequential_at_curriculum_level_is_rejected`, `test_extra_field_at_module_level_is_rejected`, `test_extra_field_at_lesson_level_is_rejected`, `test_extra_field_at_locking_level_is_rejected`) plus a positive control (`test_correctly_nested_locking_still_validates`).
- [x] Wrote 2 failing lesson-route tests in [page.test.ts](src/learningfoundry/sveltekit_template/src/routes/[module]/[lesson]/page.test.ts): a negative case (locked module → placeholder, no `<article>`) and a positive control (unlocked module → `<article>`, no "locked" text).
- [x] Wrote 1 visual-indicator regression-guard in [ModuleList.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/ModuleList.test.ts): asserts `cursor-not-allowed` + `text-gray-400` on the locked button. (Passed against existing code; pure regression guard.)
- [x] Confirmed each new test failed for the right reason before any fix code was written. The schema tests `DID NOT RAISE`; the route test rendered an `<article>` it shouldn't have.
- [x] Added `StrictModel` base class with `extra='forbid'`; converted all 11 schema classes from `BaseModel` to `StrictModel`.
- [x] Added the route's locking guard: `moduleIndex` / `lessonIndex` derived state, `isLocked` derived boolean, `blockedByTitle` derived for the placeholder copy, guarded `navigateTo` calls.
- [x] Created [LockedLessonPlaceholder.svelte](src/learningfoundry/sveltekit_template/src/lib/components/LockedLessonPlaceholder.svelte) — Lock icon, module/lesson titles, "Complete <previous>" copy, Return-to-dashboard CTA.
- [x] Verified against user's actual `learningfoundry-test/curriculum.yml`: now rejects with `curriculum.sequential — Extra inputs are not permitted` (was silently parsing as `locking.sequential = false`).
- [x] Bumped version to v0.62.1 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] `CHANGELOG.md` — v0.62.1 under "Fixed" / "Changed".
- [x] Verify: `pyve test tests/` (264 pass — was 259 + 5 new schema), `pnpm test` (173 pass — was 170 + 3 new), `pyve testenv run ruff check .` clean, `pyve testenv run mypy src/` clean.

**Out of scope:**

- **Stronger visual styling for locked modules.** The existing Lock icon + gray-400 + cursor-not-allowed is a reasonable indicator. If after seeing it actually fire in the user's project the styling feels insufficient, a UX tweak (e.g. `bg-gray-50` on the locked `<li>`, or a dedicated `aria-label`) is a small follow-up.
- **Deprecation policy for previously-tolerated extra fields.** This is a breaking change for any downstream curriculum that had benign extras. For this project there is one user and a small set of fixtures we control, so no migration path is needed; for a wider release a more graceful path (warning before the next major) might be warranted.
- **Validation-time hint messages.** Pydantic's stock `Extra inputs are not permitted [field=X]` is clear but generic. A future enhancement could intercept the most common typos (`sequential` at curriculum level, `lock` for `locked`, `lessson_sequential`) and emit "Did you mean…?" hints. Not blocking.
- **Locking enforcement at the resolver layer.** The lesson route's guard is a defense-in-depth at the *navigation* boundary; the schema's strictness is at the *ingestion* boundary. The middle layer (resolver → curriculum.json) is not strictly necessary as a third gate because both ends are now closed, but a future story could add a "no locked-default-status" invariant check in the resolver if the locking model grows more complex.
- **Refining the placeholder UX.** The current placeholder is functional but minimal. Showing a progress preview ("you're 2/3 through Module 1"), a list of remaining-to-complete lessons, or contextual tooltips is potentially valuable but separate from the failsafe-correctness fix.

---

### Story I.aa.3: v0.62.2 — Dashboard 'Start Module' CTA Reflects Locked State [Done]

Story I.aa.2 closed the URL-bar entry point for locked lessons (route-level `LockedLessonPlaceholder`). This story closes the *third* entry point: the dashboard's per-module "Start module →" / "Continue →" call-to-action button. Pre-fix, the dashboard rendered the same active-blue button for every non-complete module regardless of locking. The button visually invited a click that, post-I.aa.2, only led to the placeholder — a worse UX than not offering the click at all.

**Root cause.** [ProgressDashboard.svelte:96-105](src/learningfoundry/sveltekit_template/src/lib/components/ProgressDashboard.svelte#L96-L105) had a two-state render branch (`stats.status === 'complete'` → `✓ Complete` badge; otherwise → action button), with no awareness of *locked* as a third state. Same anti-pattern as Story I.aa.2's lesson-route gap: the locking model was enforced in *one* place (the sidebar), missed at every other entry point.

**Why this wasn't caught.** [ProgressDashboard.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/ProgressDashboard.test.ts) had thorough coverage for the `complete` vs `not_started` vs `in_progress` action rendering (Story I.r regression coverage) but no test passed `curriculum` with `locking.sequential = true` and asserted the resulting CTA shape. Same pyramid gap as I.aa.2: the helper layer (`isModuleLocked`) had thorough coverage; the integration layer ("does the dashboard CTA reflect lock state?") didn't.

**Fix.** Three lines of script + a render-branch addition in [ProgressDashboard.svelte](src/learningfoundry/sveltekit_template/src/lib/components/ProgressDashboard.svelte):
1. Import `lockedModuleIds` from `$lib/utils/locking.js` and `Lock` from `lucide-svelte`.
2. Derive `lockedModules = $derived(curriculum ? lockedModuleIds(curriculum, progress) : new Set())`.
3. Promote the per-module action area from a 2-way to a 3-way branch: `locked` → render a `<p aria-disabled="true">` with Lock icon + "Locked" text in `text-gray-400`; existing `complete` and `else` branches unchanged.
4. Module title also picks up the Lock icon and gray-400 styling for visual cohesion with the sidebar.

The locked indicator deliberately matches the sidebar's idiom (Lucide Lock + `text-gray-400`) so the dashboard and sidebar tell the same story.

**Tasks:**

- [x] Wrote failing test in [ProgressDashboard.test.ts](src/learningfoundry/sveltekit_template/src/lib/components/ProgressDashboard.test.ts): mount with `locking.sequential = true`, module 1 not complete → module 2 locked. Asserts module 2's card has no `<button>`, contains "Locked" text, and renders a `lucide-lock` SVG. Positive control: module 1 still has the "Start module →" button.
- [x] Confirmed test failed for the right reason (Start-module button rendered for module 2).
- [x] Implemented the 3-way branch in `ProgressDashboard.svelte` and wired the title-row Lock icon.
- [x] Verified all existing dashboard tests still pass (the 2-way branch test now exercises the unlocked path explicitly via `progress` shape; `curriculum` is optional so existing tests that don't pass it still see all modules as unlocked).
- [x] Bumped version to v0.62.2 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] `CHANGELOG.md` — v0.62.2 under "Fixed".
- [x] Verify: `pyve test tests/` (264 pass), `pnpm test` (174 pass — was 173 + 1 new), `ruff check .` clean, `mypy src/` clean.

**Out of scope:**

- **Card-wide muting for locked modules.** Currently the title gets the gray-400 + Lock treatment and the CTA area gets the "Locked" indicator; the description, progress bar, and assessment lines stay full-color. A more aggressive treatment (gray-tinted border, faded description, gray progress bar) might better communicate "this whole card is gated." Easy follow-up if the current treatment doesn't read as locked clearly enough.
- **Auditing other navigation surfaces for the same pattern.** Sidebar (Story I.j), lesson route (Story I.aa.2), and dashboard CTA (this story) cover the three entry points a learner uses. If a future story adds a fourth (e.g. a "next module" CTA at the end of a lesson), it must consult `lockedModuleIds` too — but the pattern is now established.
- **Tooltip on the Locked indicator.** Hovering "Locked" could surface "Complete <previous module> to unlock" for symmetry with the lesson-route placeholder. Not blocking; the placeholder text on the route already explains.

---

### Story I.bb: UI Surfacing of `WasmAssetMissingError` [Planned]

Story I.aa hardened the asset pipeline so `/sql-wasm.wasm` reaches `static/` reliably, and exported a typed `WasmAssetMissingError` from [database.ts](src/learningfoundry/sveltekit_template/src/lib/db/database.ts) that gets thrown when the asset 404s at runtime. What's still missing: **the learner has no idea when recording is failing.** Today a thrown `WasmAssetMissingError` propagates up through `progress.ts` (`ProgressRepo` chokepoint, Story I.w) into UI call sites that just `await` and silently no-op the rejection. The CLI logs are the only signal — no help to a learner using a deployed app.

**What "done" looks like:**

A learner who hits a missing-wasm scenario (asset-pipeline regression, deploy misconfiguration, browser cache poisoning, network partition) sees a persistent, non-blocking banner — "Progress recording is paused. Refresh to retry." — and a refresh action. Their existing in-memory progress for the current session continues to render (read-from-IDB-once may have already populated stores), but writes are best-effort and the banner makes the tradeoff visible. Once a refresh succeeds, the banner clears.

**Design considerations (to settle in story refinement, not pre-decided here):**

- Where the catch lives. Options: (a) wrap each `progress.ts` write call site in UI components; (b) add a layout-level `<svelte:boundary>` that catches uncaught rejections from `progress.ts`; (c) move detection upstream — initialise the `Database` once at layout mount and surface init failures as a layout-level reactive store. (c) is probably right because it converts the failure from "every write rejects independently" into "one signal that the whole DB is unavailable." Confirm during implementation.
- Whether `progress.ts` writes should *swallow* `WasmAssetMissingError` (since the banner already surfaces the failure) or let it propagate. Probably swallow — the rejection is informational once the banner is up; UI components shouldn't have to handle it.
- Whether the read path (`getLessonProgress`, `listAllProgress`) should fall back to "empty" or surface the error. Read failures during initial render are a worse UX than write failures — render an empty dashboard with the banner, *not* an error page.
- Telemetry hook for "this learner hit a wasm-missing event" so future deploy regressions get caught faster than this one did. May be out of scope until there's a telemetry pipeline.

**Tasks (draft — refine when this story is picked up):**

- [ ] Decide catch placement (probably layout-level init store; confirm).
- [ ] Implement the banner component (copy, iconography, refresh CTA).
- [ ] Wire `WasmAssetMissingError` detection into the chosen catch site.
- [ ] Decide swallow-vs-propagate for `progress.ts` write methods; document the rule in the file's module comment.
- [ ] Verify the read path handles a missing-wasm `Database` without rendering an error page (empty state + banner).
- [ ] Add a vitest case that mounts the layout with a 404'd wasm fetch and asserts the banner renders.
- [ ] Add a vitest case that mounts the layout with a working wasm and asserts the banner does not render.
- [ ] Update [features.md](docs/specs/features.md) with the recording-paused user-visible state as a documented requirement (closes the requirements gap that Story I.aa identified).
- [ ] Bump version, update CHANGELOG.
- [ ] Verify: `pyve test`, `pnpm test`, `pnpm e2e`, ruff, mypy.

**Out of scope:**

- **Telemetry / error reporting beyond the in-app banner.** Worth doing, but couples to a not-yet-existent telemetry pipeline.
- **Auto-retry mechanism.** A "retry now" button is fine; an automatic background retry loop adds complexity (backoff, jitter, exponential schedule) without clear demand. The refresh action is a reliable manual recovery path.
- **Generalising the banner pattern to other recoverable errors.** Tempting but premature — the only known case today is `WasmAssetMissingError`. If a second case shows up, generalise then.

---

### Story I.cc: Investigate pnpm Lifecycle-Script Reliability [Planned]

A discovery story, not a fix story. Scoped to gather evidence and decide whether further work is warranted.

**Background.** During earlier setup of `learningfoundry-test`, the user reported that "pnpm has some wiring problems not passing certain params to npm and could only get it to work using npm directly." Story I.aa removed the template's `postinstall` hook (which had been one symptom of pnpm lifecycle-script unreliability) by moving the wasm-asset copy into the Python pipeline. That fix unblocks recording, but it sidesteps rather than diagnoses the underlying environmental issue. The risk: future template additions that rely on pnpm lifecycle scripts (`prepare`, `prepublish`, `prepack`, custom `pre*` / `post*` hooks for `dev` / `build` / `test`) may silently misbehave in the same way.

**What "done" looks like:**

A short investigation note (probably a section in [docs/specs/project-essentials.md](docs/specs/project-essentials.md) under "Architecture Quirks" or its own subsection) that captures: which lifecycle scripts pnpm reliably runs in this project's configuration, what the user's specific wiring grief was, whether it reproduces today, and a one-paragraph guideline for future template work ("don't rely on pnpm `postinstall`; do these things from the Python pipeline instead").

If the investigation surfaces an actionable bug (e.g. a pnpm setting we should pin in [.npmrc](src/learningfoundry/sveltekit_template/.npmrc) or a pnpm version range we should require in `engines`), file a follow-up *fix* story rather than expanding this one.

**Investigation plan (draft):**

- [ ] Reconstruct the user's earlier pnpm-vs-npm grief — what command, what params, what failure mode, what was the workaround. Likely the cleanest path is just to ask the user; failing that, scrape git history / chat for the relevant context.
- [ ] In a clean `learningfoundry-test/dist/` (or a fresh tmp output): seed a noop `postinstall` (`echo HELLO > postinstall.marker`); run `pnpm install`; check whether `postinstall.marker` was created. Repeat for `prepare`, `prepublish`. Record results.
- [ ] Check pnpm version in user environment vs. what `engines` (if any) declares; check for `.npmrc` settings (`enable-pre-post-scripts`, `node-linker`, `package-manager-strict`) in user environment, project, and global config.
- [ ] If lifecycle scripts work fine on a clean test: the original grief was version-specific or has self-resolved. Document and close.
- [ ] If lifecycle scripts genuinely don't fire: bisect by `.npmrc` / pnpm version to identify the cause. Decide between (a) pinning settings in the project, (b) adding a `engines.pnpm` constraint, (c) explicitly documenting "we don't use pnpm lifecycle scripts; here's why" and constraining future template work.
- [ ] Update [docs/specs/project-essentials.md](docs/specs/project-essentials.md) with the findings.
- [ ] Bump version + CHANGELOG only if this story produces code/config changes (a docs-only outcome may not need a version bump — match how other docs-only changes were handled in the project).

**Out of scope:**

- **Switching the project from pnpm to npm.** Even if pnpm has ongoing issues, the migration cost likely outweighs the benefit; the Story I.aa fix already removes the load-bearing dependency.
- **Investigating other Node tool reliability issues** (vite, vitest, playwright). Scoped to pnpm lifecycle scripts specifically.
- **Adding lifecycle-script-dependent template features** ahead of this investigation. If a future story wants to add e.g. a `prepare` hook to the template, it should block on this story landing first.

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
