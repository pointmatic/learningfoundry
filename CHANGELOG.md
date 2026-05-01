# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
