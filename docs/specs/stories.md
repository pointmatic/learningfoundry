# stories.md -- learningfoundry (Python 3.12 + SvelteKit)

This document breaks the `learningfoundry` project into an ordered sequence of small, independently completable stories grouped into phases. Each story has a checklist of concrete tasks. Stories are organized by phase and reference modules defined in `tech-spec.md`.

Stories with code changes include a version number (e.g., v0.1.0). Stories with only documentation or polish changes omit the version number. The version follows semantic versioning and is bumped per story. Stories are marked with `[Planned]` initially and changed to `[Done]` when completed.

For a high-level concept (why), see `concept.md`. For requirements and behavior (what), see `features.md`. For implementation details (how), see `tech-spec.md`. For project-specific must-know facts, see `project-essentials.md` (`plan_phase` appends new facts per phase).

---

## Phase A: Foundation

### Story A.a: v0.1.0 Hello World — Minimal Runnable Package [Done]

The smallest runnable artifact proving the environment is wired up.

- [x] Verify `LICENSE` (Apache-2.0) is present in project root
- [x] Establish copyright header format (Apache-2.0) for Python/Shell, TypeScript/JS, and Svelte/HTML files
- [x] Create `pyproject.toml` with hatchling build backend, project metadata, and `learningfoundry` console script entry point
- [x] Create `README.md` with project name, one-liner description, and license badge
- [x] Create `CHANGELOG.md` (Keep a Changelog format, `[Unreleased]` section)
- [x] Update `.gitignore` with Node/SvelteKit patterns (`node_modules/`, `.svelte-kit/`, `.output/`, `*.tsbuildinfo`)
- [x] Create `src/learningfoundry/__init__.py` with `__version__ = "0.1.0"`
- [x] Create `src/learningfoundry/py.typed` (PEP 561 marker)
- [x] Create `src/learningfoundry/cli.py` with a Click group and a `--version` flag
- [x] Verify: `pyve run python -m learningfoundry --version` prints `0.1.0`

### Story A.b: v0.2.0 PyPI Publish Workflow and Name Reservation [Done]

Automated publishing to reserve the `learningfoundry` name on PyPI early.

- [x] Create `.github/workflows/publish.yml`
  - [x] Trigger: push tag matching `v*`
  - [x] Steps: checkout, build sdist + wheel (`python -m build`), publish to PyPI via `twine` or `pypa/gh-action-pypi-publish`
  - [x] Use OIDC trusted publishing (preferred) or `PYPI_API_TOKEN` secret
- [x] Tag v0.2.0 and push to trigger initial publish, reserving the `learningfoundry` name on PyPI
- [x] Verify: tagged push triggers publish, package appears on PyPI

### Story A.c: v0.3.0 End-to-End Stack Spike [Done]

Throwaway script wiring the full critical path: YAML parse → content resolve → SvelteKit output.

- [x] Create `scripts/spike_e2e.py`
  - [x] Hard-code a minimal curriculum dict (1 module, 1 lesson, 1 text block)
  - [x] Write it as a YAML string, parse with PyYAML
  - [x] Read a stub markdown file and attach it as resolved content
  - [x] Copy a minimal SvelteKit skeleton to a temp output dir
  - [x] Write a `curriculum.json` into the skeleton
  - [x] Print summary: "Generated SvelteKit project at <path>"
- [x] Create `scripts/fixtures/spike-curriculum.yml` and `scripts/fixtures/content/lesson-01.md`
- [x] Bump version to v0.3.0
- [x] Update CHANGELOG.md
- [x] Verify: `pyve run python scripts/spike_e2e.py` produces output dir with `curriculum.json`

### Story A.d: v0.4.0 Exception Hierarchy and Logging [Done]

Foundation error handling and logging used by all subsequent modules.

- [x] Create `src/learningfoundry/exceptions.py` with full hierarchy: `LearningFoundryError`, `ConfigError`, `CurriculumVersionError`, `CurriculumValidationError`, `ContentResolutionError`, `IntegrationError`, `GenerationError`
- [x] Create `src/learningfoundry/logging_config.py` with `setup_logging(level, output)` using stdlib `logging`
- [x] Unit tests in `tests/test_exceptions.py` (verify hierarchy, string representations)
- [x] Bump version to v0.4.0
- [x] Update CHANGELOG.md
- [x] Verify: exceptions are importable, logging outputs to stdout at default INFO level

### Story A.e: v0.5.0 Global Configuration [Done]

Settings model and config loading with precedence merging.

- [x] Create `src/learningfoundry/config.py` with `LoggingConfig`, `AppConfig` dataclasses and `load_config()` function
- [x] Implement precedence: CLI flags > config file (`~/.config/learningfoundry/config.yml`) > built-in defaults
- [x] Handle malformed YAML (raise `ConfigError`), unknown keys (warn and ignore)
- [x] Create `tests/test_config.py`
  - [x] Test defaults when no config file exists
  - [x] Test config file overrides defaults
  - [x] Test CLI overrides config file
  - [x] Test malformed config raises `ConfigError`
  - [x] Test unknown keys produce warning
- [x] Bump version to v0.5.0
- [x] Update CHANGELOG.md

## Phase B: Core Services

### Story B.a: v0.6.0 Curriculum YAML Schema (Pydantic Models) [Done]

Pydantic models for the v1 curriculum YAML schema.

- [x] Create `src/learningfoundry/schema_v1.py` with all models: `AssessmentRef`, `TextBlock`, `VideoBlock`, `QuizBlock`, `ExerciseBlock`, `VisualizationBlock`, `ContentBlock` union, `Lesson`, `Module`, `CurriculumDef`, `CurriculumV1`
- [x] Implement validators: YouTube URL format, hyphenated lowercase IDs, at least one module, at least one lesson, unique IDs
- [x] Create `tests/test_schema_v1.py`
  - [x] Valid curriculum passes
  - [x] Missing required fields
  - [x] Invalid ID format (camelCase, underscored, integers)
  - [x] Duplicate module/lesson IDs
  - [x] Invalid YouTube URL
  - [x] Zero modules / zero lessons
- [x] Bump version to v0.6.0
- [x] Update CHANGELOG.md

### Story B.b: v0.7.0 YAML Curriculum Parser [Done]

Parser that loads YAML, extracts version, dispatches to schema.

- [x] Create `src/learningfoundry/parser.py` with `parse_curriculum()` and `_dispatch_parser()`
- [x] Handle: missing version field, unsupported major version, malformed YAML
- [x] Create `tests/test_parser.py`
  - [x] Valid YAML parses to `CurriculumV1`
  - [x] Missing `version` raises `CurriculumVersionError`
  - [x] Unsupported version raises `CurriculumVersionError`
  - [x] Malformed YAML raises appropriate error
- [x] Create test fixture: `tests/fixtures/valid-curriculum.yml`
- [x] Bump version to v0.7.0
- [x] Update CHANGELOG.md

### Story B.c: v0.8.0 Provider Protocols and Stubs [Done]

Integration protocols and v1 stub implementations.

- [x] Create `src/learningfoundry/integrations/__init__.py`
- [x] Create `src/learningfoundry/integrations/protocols.py` with `QuizProvider`, `ExerciseProvider`, `VisualizationProvider` protocols
- [x] Create `src/learningfoundry/integrations/nbfoundry_stub.py` (`NbfoundryStub`) — returns placeholder dict with `"status": "stub"`
- [x] Create `src/learningfoundry/integrations/d3foundry_stub.py` (`D3foundryStub`) — returns placeholder dict with `"status": "stub"`
- [x] Create `tests/test_integrations/test_nbfoundry_stub.py` and `tests/test_integrations/test_d3foundry_stub.py`
  - [x] Verify stub return structure matches `ExerciseContent` / `VisualizationContent` TypeScript interfaces
- [x] Bump version to v0.8.0
- [x] Update CHANGELOG.md

### Story B.d: v0.9.0 quizazz Integration [Done]

QuizProvider implementation delegating to `quizazz_builder`.

- [x] Create `src/learningfoundry/integrations/quizazz.py` (`QuizazzProvider`)
  - [x] Resolve ref path relative to base dir
  - [x] Delegate to `quizazz_builder.compile_assessment()`
  - [x] Wrap errors in `IntegrationError`
- [x] Create `tests/test_integrations/test_quizazz.py`
  - [x] Mock `quizazz_builder` — verify delegation and error wrapping
- [x] Bump version to v0.9.0
- [x] Update CHANGELOG.md
- [x] Verify: `quizazz-builder` is listed in `[project.optional-dependencies]`

### Story B.e: v0.10.0 Content Resolver [Done]

Resolve all content references in a parsed curriculum.

- [x] Create `src/learningfoundry/resolver.py` with `ResolvedCurriculum`, `ResolvedModule`, `ResolvedLesson`, `ResolvedContentBlock` dataclasses and `resolve_curriculum()` function
- [x] Implement resolution for each block type: text (read markdown), video (validate URL), quiz (delegate to `QuizProvider`), exercise (delegate to `ExerciseProvider`), visualization (delegate to `VisualizationProvider`)
- [x] Resolve pre/post assessments on modules
- [x] Raise `ContentResolutionError` with block location context
- [x] Create `tests/test_resolver.py`
  - [x] Valid resolution with mocked providers
  - [x] Missing markdown file raises `ContentResolutionError`
  - [x] Invalid YouTube URL raises `ContentResolutionError`
  - [x] Provider error wrapped with block location
  - [x] Empty markdown file produces warning
- [x] Bump version to v0.10.0
- [x] Update CHANGELOG.md

## Phase C: Pipeline and Orchestration

### Story C.a: v0.11.0 Pipeline Orchestrator [Done]

Wire parse → resolve → generate into a single pipeline.

- [x] Create `src/learningfoundry/pipeline.py` with `run_build()`, `run_validate()`, `run_preview()`
- [x] `run_build()`: parse → resolve → generate, log progress at each stage, fail fast on error
- [x] `run_validate()`: parse → resolve (validation only), report result
- [x] `run_preview()`: build → `pnpm install` → `pnpm run dev --port`
- [x] Create `tests/test_pipeline.py`
  - [x] End-to-end with fixture curriculum (mocked generator for unit test)
  - [x] Validate-only mode catches errors without generating
- [x] Bump version to v0.11.0
- [x] Update CHANGELOG.md

### Story C.b: v0.12.0 SvelteKit Generator — Template Copy and curriculum.json [Done]

Generate a SvelteKit project from resolved curriculum.

- [x] Create `src/learningfoundry/generator.py` with `generate_app()`
- [x] Copy `sveltekit_template/` to output dir (atomic: write to temp, then move)
- [x] Serialize `ResolvedCurriculum` to `curriculum.json` in the output `static/` dir
- [x] Overwrite existing output dir with warning
- [x] Create `tests/test_generator.py`
  - [x] Output dir contains expected files (`package.json`, `svelte.config.js`, `curriculum.json`)
  - [x] `curriculum.json` content matches input
  - [x] Overwrite behavior
- [x] Bump version to v0.12.0
- [x] Update CHANGELOG.md

## Phase D: SvelteKit Frontend Template

### Story D.a: v0.13.0 SvelteKit Skeleton — Project Config and Shell [Done]

Minimal SvelteKit template that builds and serves.

- [x] Create `sveltekit_template/package.json` with dependencies: `svelte`, `@sveltejs/kit`, `@sveltejs/adapter-static`, `sql.js`, `lucide-svelte`, dev deps: `typescript`, `tailwindcss`, `@tailwindcss/vite`, `vitest`, `eslint`, `prettier`, `prettier-plugin-svelte`
- [x] Create `sveltekit_template/svelte.config.js` with `adapter-static`
- [x] Create `sveltekit_template/vite.config.ts`
- [x] Create `sveltekit_template/tsconfig.json`
- [x] Create `sveltekit_template/src/app.html` (SvelteKit shell)
- [x] Create `sveltekit_template/src/app.css` (Tailwind imports)
- [x] Bump version to v0.13.0
- [x] Update CHANGELOG.md
- [x] Verify: `pnpm install && pnpm build` succeeds in the template dir

### Story D.b: v0.14.0 TypeScript Types and Curriculum Store [Done]

Type definitions and Svelte stores for the frontend.

- [x] Create `sveltekit_template/src/lib/types/index.ts` with all interfaces: `Curriculum`, `Module`, `Lesson`, `ContentBlock`, `QuizManifest`, `ExerciseContent`, `VisualizationContent`, progress types
- [x] Create `sveltekit_template/src/lib/stores/curriculum.ts` — load `curriculum.json`, expose curriculum state and navigation helpers
- [x] Bump version to v0.14.0
- [x] Update CHANGELOG.md
- [x] Verify: TypeScript compiles without errors

### Story D.c: v0.15.0 SQLite Progress Database [Done]

In-browser SQLite for learner progress tracking.

- [x] Create `sveltekit_template/src/lib/db/database.ts` — sql.js init, IndexedDB persistence, schema creation (tables: `lesson_progress`, `quiz_scores`, `exercise_status`)
- [x] Create `sveltekit_template/src/lib/db/progress.ts` — CRUD: mark lesson complete, save quiz score, update exercise status, query module progress
- [x] Create `sveltekit_template/src/lib/db/index.ts` (barrel export)
- [x] Copy `sql-wasm.wasm` to `sveltekit_template/static/` via postinstall script
- [x] Bump version to v0.15.0
- [x] Update CHANGELOG.md
- [x] Verify: database initializes on page load, CRUD operations work

### Story D.d: v0.16.0 Content Block Components [Done]

Svelte components for rendering each content block type.

- [x] Create `sveltekit_template/src/lib/components/TextBlock.svelte` — render HTML from markdown
- [x] Create `sveltekit_template/src/lib/components/VideoBlock.svelte` — YouTube embed
- [x] Create `sveltekit_template/src/lib/components/QuizBlock.svelte` — render quizazz manifest, scoring, write to SQLite
- [x] Create `sveltekit_template/src/lib/components/ExerciseBlock.svelte` — render exercise content or stub placeholder
- [x] Create `sveltekit_template/src/lib/components/VisualizationBlock.svelte` — render visualization or stub placeholder
- [x] Create `sveltekit_template/src/lib/components/PlaceholderBlock.svelte` — generic "coming soon" placeholder
- [x] Create `sveltekit_template/src/lib/components/ContentBlock.svelte` — dispatcher by block type
- [x] Create `sveltekit_template/src/lib/utils/markdown.ts` — markdown-to-HTML utility
- [x] Bump version to v0.16.0
- [x] Update CHANGELOG.md

### Story D.e: v0.17.0 Navigation and Progress UI [Done]

Navigation components and progress dashboard.

- [x] Create `sveltekit_template/src/lib/components/ModuleList.svelte` — sidebar module navigation with progress indicators
- [x] Create `sveltekit_template/src/lib/components/LessonList.svelte` — lesson list within a module
- [x] Create `sveltekit_template/src/lib/components/Navigation.svelte` — prev/next lesson nav
- [x] Create `sveltekit_template/src/lib/components/ProgressBar.svelte` — visual progress indicator
- [x] Create `sveltekit_template/src/lib/components/ProgressDashboard.svelte` — per-module completion, quiz scores overview
- [x] Bump version to v0.17.0
- [x] Update CHANGELOG.md

### Story D.f: v0.18.0 Route Pages and Layout [Done]

SvelteKit routes tying everything together.

- [x] Create `sveltekit_template/src/routes/+layout.svelte` — app shell with sidebar navigation
- [x] Create `sveltekit_template/src/routes/+page.svelte` — landing page / progress dashboard
- [x] Create `sveltekit_template/src/routes/[module]/[lesson]/+page.svelte` — lesson page rendering content blocks via `LessonView.svelte`
- [x] Create `sveltekit_template/src/lib/components/LessonView.svelte` — lesson content renderer
- [x] Bump version to v0.18.0
- [x] Update CHANGELOG.md
- [x] Verify: full app builds, navigates modules/lessons, renders all block types

## Phase E: CLI Interface

### Story E.a: v0.19.0 CLI Build and Validate Commands [Done]

Wire CLI to the pipeline orchestrator.

- [x] Update `src/learningfoundry/cli.py`: implement `build` and `validate` subcommands
  - [x] `build`: load config, call `run_build()`, handle errors with exit codes
  - [x] `validate`: load config, call `run_validate()`, report result
  - [x] Shared flags: `--config`, `--log-level`
- [x] Create `tests/test_cli.py`
  - [x] `build` produces output directory with fixture curriculum
  - [x] `validate` reports OK for valid curriculum
  - [x] `validate` reports errors for invalid curriculum
  - [x] `--help` exits 0
  - [x] Exit codes match spec (1=validation, 2=resolution, 3=generation, 4=config)
- [x] Bump version to v0.19.0
- [x] Update CHANGELOG.md

### Story E.b: v0.20.0 CLI Preview Command [Done]

Build and serve locally.

- [x] Implement `preview` subcommand in `cli.py`
  - [x] Call `run_preview()` — build, `pnpm install`, start dev server
  - [x] Accept `--port` flag (default 5173)
  - [x] Print local URL
- [x] Add test in `tests/test_cli.py` for preview (verify build step runs; dev server is an integration concern)
- [x] Bump version to v0.20.0
- [x] Update CHANGELOG.md

## Phase F: Testing and Quality

### Story F.a: v0.21.0 Test Suite Completion [Done]

Fill any test gaps and ensure full coverage of high-value paths.

- [x] Audit existing tests against tech-spec testing strategy
- [x] Add any missing unit tests for edge cases (empty curriculum, all block types, large curriculum)
- [x] Add integration test: full build with fixture curriculum containing all content block types
- [x] Bump version to v0.21.0
- [x] Update CHANGELOG.md
- [x] Verify: `pyve test` passes all tests

### Story F.b: v0.22.0 Linting, Formatting, and Type Checking [Done]

Enforce code quality tooling.

- [x] Create `ruff.toml` or `[tool.ruff]` section in `pyproject.toml` with project-appropriate rules
- [x] Configure mypy in `pyproject.toml` (`--strict`)
- [x] Run `pyve testenv run ruff check .` — fix all issues
- [x] Run `pyve testenv run mypy src/` — fix all type errors
- [x] Create `requirements-dev.txt` with all the necessary development dependencies. 
- [x] Bump version to v0.22.0
- [x] Update CHANGELOG.md
- [x] Verify: both pass cleanly

### Story F.c: v0.23.0 SvelteKit Smoke Test [Done]

Verify the generated app compiles end-to-end.

- [x] Create a test fixture curriculum with all block types (text, video, quiz, exercise, visualization)
- [x] Run `learningfoundry build` on the fixture
- [x] Run `pnpm install && pnpm build` in the output directory
- [x] Verify: build succeeds with no errors

## Phase G: Documentation and Release

### Story G.a: v0.24.0 README and Changelog [Done]

User-facing documentation.

- [x] Write `README.md`: project description, installation, quick start, CLI usage, curriculum YAML format, development setup
- [x] Create `CHANGELOG.md` with entries for v0.1.0 through current version
- [x] Verify: README instructions work on a clean checkout

### Story G.b: v0.25.0 Final Polish and Release Prep [Done]

Last checks before initial release.

- [x] Review `pyproject.toml` metadata (description, classifiers, URLs)
- [x] Verify `sveltekit_template/` is included in sdist/wheel builds
- [x] Test `pip install` from built wheel in a clean venv
- [x] Bump version to v0.25.0
- [x] Update CHANGELOG.md
- [x] Tag release as v0.25.0

## Phase H: CI/CD and Automation

### Story H.a: v0.26.0 GitHub Actions — Lint and Test on Push [Done]

Catch regressions on every push.

- [x] Create `.github/workflows/ci.yml`
  - [x] Trigger: push to `main`, pull requests
  - [x] Matrix: Python 3.12, latest Ubuntu
  - [x] Steps: checkout, `actions/setup-python`, install deps, `ruff check .`, `mypy src/`, `pytest`
- [x] Verify: workflow passes on push

### Story H.b: v0.27.0 GitHub Actions — Coverage Badge [Done]

Visible test coverage in the repo.

- [x] Add `pytest-cov` to dev dependencies
- [x] Update CI workflow to run `pytest --cov=src/learningfoundry --cov-report=xml`
- [x] Integrate with Codecov via `codecov/codecov-action@v4`
- [x] Add coverage badge to `README.md`
- [x] Verify: badge renders and updates on push

### Story H.c: v0.28.0 Fix 'quizazz' Extra to Match Published Package [Done]

`pip install "learningfoundry[quizazz]"` failed because the extra pointed at the non-existent PyPI package `quizazz-builder`. Per `docs/specs/quizazz-README.md`, the package is published as `quizazz` (both the PyPI distribution name and the Python import name).

- [x] Update `pyproject.toml`: `[project.optional-dependencies] quizazz` → `quizazz>=0.1`; `[[tool.mypy.overrides]] module = "quizazz"`
- [x] Update `src/learningfoundry/integrations/quizazz.py`: `from quizazz import compile_assessment`; docstrings and error messages reference `quizazz`
- [x] Update `tests/test_integrations/test_quizazz.py`: `sys.modules` mocks and `ImportError` match pattern use `quizazz`
- [x] Update `src/learningfoundry/resolver.py` docstring
- [x] Update `README.md` quiz block link
- [x] Bump version to v0.28.0
- [x] Update CHANGELOG.md
- [x] Verify: `pyve test` passes (195/195), `ruff` and `mypy` clean
- [x] Verify: `pip install "learningfoundry[quizazz]"` resolves in a clean venv after v0.28.0 is published to PyPI

### Story H.d: v0.29.0 Fix Lesson Navigation + Frontend Unit Tests [Done]

Lesson content never rendered after clicking "Start module" / Next / Previous. `navigateTo`, `navigateNext`, and `navigatePrev` in the SvelteKit template only updated the `currentPosition` Svelte store; they never changed the URL. Because lesson content is mounted by the dynamic route `/[module]/[lesson]/+page.svelte`, the route was never visited and `LessonView` (which renders the inlined markdown) never mounted — the left nav title updated, but the content area stayed on the home dashboard.

The template had no frontend test suite, so this regression went uncaught. Added vitest + tests for the navigation helpers to prevent recurrence.

**Bug fix:**

- [x] `src/learningfoundry/sveltekit_template/src/lib/stores/curriculum.ts` — `navigateTo` calls `goto('/${moduleId}/${lessonId}')`; `navigateNext`/`navigatePrev` delegate to `navigateTo`

**Frontend unit tests:**

- [x] Add `jsdom` to `sveltekit_template/package.json` devDependencies (`vitest` was already present; `@vitest/ui` skipped — not needed for headless CI)
- [x] Extend `vite.config.ts` with vitest config (`environment: 'jsdom'`, `include: src/**/*.{test,spec}.{js,ts}`)
- [x] `test` script `vitest run` already present in `package.json`
- [x] Create `src/lib/stores/curriculum.test.ts` (9 cases):
  - [x] `navigateTo` calls `goto` with `/{moduleId}/{lessonId}` and updates `currentPosition`
  - [x] `navigateNext` advances within a module
  - [x] `navigateNext` crosses module boundaries
  - [x] `navigateNext` is a no-op past the final lesson
  - [x] `navigateNext` is a no-op when `currentPosition` is null
  - [x] `navigatePrev` reverses through lessons within a module
  - [x] `navigatePrev` reverses across module boundaries
  - [x] `navigatePrev` is a no-op before the first lesson
  - [x] `navigatePrev` is a no-op when `currentPosition` is null
  - [x] Mock `$app/navigation`'s `goto` via `vi.mock`; stub global `fetch` to seed the curriculum readable
- [x] Update `tests/test_smoke_sveltekit.py` with `test_pnpm_test_passes` to also run `pnpm test` after `pnpm install`
- [x] Bump version to v0.29.0
- [x] Update CHANGELOG.md
- [x] Verify: `pyve test -m smoke` passes — 7/7 (Python smoke + vitest); full suite 195/195; ruff + mypy clean

### Story H.e: v0.30.0 Disable SSR/Prerender in Generated SPA [Done]

Every `learningfoundry build` run printed `Cannot call fetch eagerly during server-side rendering with relative URL (/curriculum.json)` errors. SvelteKit's prerender pass subscribes to the `curriculum` readable during SSR of `+layout.svelte`, and the readable's start function calls `fetch('/curriculum.json')` — a relative URL, which is illegal on the server. The generated app is a pure CSR SPA (runtime curriculum fetch, IndexedDB, sql.js/WASM) and was never intended to render on the server. `svelte.config.js` already uses `adapter-static` with `fallback: 'index.html'`, so the SPA fallback handles every route client-side without prerendering.

- [x] Create `src/learningfoundry/sveltekit_template/src/routes/+layout.ts` exporting `ssr = false` and `prerender = false`
- [x] Bump version to v0.30.0
- [x] Update CHANGELOG.md
- [x] Verify: `pyve test -m smoke` passes 7/7 with no SSR errors in build output

### Story H.f: v0.31.0 Wire "Finish" Button to Return Home [Done]

Clicking "Finish" on the final lesson did nothing visible. `Navigation.goNext()` calls `onComplete?.()` when there is no next lesson; `LessonView.handleNavComplete()` marks the lesson complete (IndexedDB) and bubbles via its own `oncomplete` prop. But `[module]/[lesson]/+page.svelte` never passed an `oncomplete` handler, so the chain ended silently — the lesson was marked complete but the learner stayed on the same page with no feedback.

- [x] `src/learningfoundry/sveltekit_template/src/routes/[module]/[lesson]/+page.svelte` — add `handleLessonComplete()` that calls `goto('/')`; pass it as `oncomplete` to `<LessonView>`
- [x] Bump version to v0.31.0
- [x] Update CHANGELOG.md
- [x] Verify: `pyve test -m smoke` passes 7/7


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
- **Pre/post assessment gating** — Module access control based on quiz scores
- **Progress export/import** — Sync or backup learner progress
- **Spaced repetition / adaptive sequencing**
- **Multi-curriculum dashboard**
