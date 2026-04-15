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

### Story B.d: v0.9.0 quizazz Integration [Planned]

QuizProvider implementation delegating to `quizazz_builder`.

- [ ] Create `src/learningfoundry/integrations/quizazz.py` (`QuizazzProvider`)
  - [ ] Resolve ref path relative to base dir
  - [ ] Delegate to `quizazz_builder.validator.validate_file()` and `quizazz_builder.compiler.compile_quiz()`
  - [ ] Wrap errors in `IntegrationError`
- [ ] Create `tests/test_integrations/test_quizazz.py`
  - [ ] Mock `quizazz_builder` — verify delegation and error wrapping
- [ ] Bump version to v0.9.0
- [ ] Update CHANGELOG.md
- [ ] Verify: `quizazz-builder` is listed in `[project.optional-dependencies]`

### Story B.e: v0.10.0 Content Resolver [Planned]

Resolve all content references in a parsed curriculum.

- [ ] Create `src/learningfoundry/resolver.py` with `ResolvedCurriculum`, `ResolvedModule`, `ResolvedLesson`, `ResolvedContentBlock` dataclasses and `resolve_curriculum()` function
- [ ] Implement resolution for each block type: text (read markdown), video (validate URL), quiz (delegate to `QuizProvider`), exercise (delegate to `ExerciseProvider`), visualization (delegate to `VisualizationProvider`)
- [ ] Resolve pre/post assessments on modules
- [ ] Raise `ContentResolutionError` with block location context
- [ ] Create `tests/test_resolver.py`
  - [ ] Valid resolution with mocked providers
  - [ ] Missing markdown file raises `ContentResolutionError`
  - [ ] Invalid YouTube URL raises `ContentResolutionError`
  - [ ] Provider error wrapped with block location
  - [ ] Empty markdown file produces warning
- [ ] Bump version to v0.10.0
- [ ] Update CHANGELOG.md

## Phase C: Pipeline and Orchestration

### Story C.a: v0.11.0 Pipeline Orchestrator [Planned]

Wire parse → resolve → generate into a single pipeline.

- [ ] Create `src/learningfoundry/pipeline.py` with `run_build()`, `run_validate()`, `run_preview()`
- [ ] `run_build()`: parse → resolve → generate, log progress at each stage, fail fast on error
- [ ] `run_validate()`: parse → resolve (validation only), report result
- [ ] `run_preview()`: build → `pnpm install` → `pnpm run dev --port`
- [ ] Create `tests/test_pipeline.py`
  - [ ] End-to-end with fixture curriculum (mocked generator for unit test)
  - [ ] Validate-only mode catches errors without generating
- [ ] Bump version to v0.11.0
- [ ] Update CHANGELOG.md

### Story C.b: v0.12.0 SvelteKit Generator — Template Copy and curriculum.json [Planned]

Generate a SvelteKit project from resolved curriculum.

- [ ] Create `src/learningfoundry/generator.py` with `generate_app()`
- [ ] Copy `sveltekit_template/` to output dir (atomic: write to temp, then move)
- [ ] Serialize `ResolvedCurriculum` to `curriculum.json` in the output `static/` dir
- [ ] Overwrite existing output dir with warning
- [ ] Create `tests/test_generator.py`
  - [ ] Output dir contains expected files (`package.json`, `svelte.config.js`, `curriculum.json`)
  - [ ] `curriculum.json` content matches input
  - [ ] Overwrite behavior
- [ ] Bump version to v0.12.0
- [ ] Update CHANGELOG.md

## Phase D: SvelteKit Frontend Template

### Story D.a: v0.13.0 SvelteKit Skeleton — Project Config and Shell [Planned]

Minimal SvelteKit template that builds and serves.

- [ ] Create `sveltekit_template/package.json` with dependencies: `svelte`, `@sveltejs/kit`, `@sveltejs/adapter-static`, `sql.js`, `lucide-svelte`, dev deps: `typescript`, `tailwindcss`, `@tailwindcss/vite`, `vitest`, `eslint`, `prettier`, `prettier-plugin-svelte`
- [ ] Create `sveltekit_template/svelte.config.js` with `adapter-static`
- [ ] Create `sveltekit_template/vite.config.ts`
- [ ] Create `sveltekit_template/tsconfig.json`
- [ ] Create `sveltekit_template/src/app.html` (SvelteKit shell)
- [ ] Create `sveltekit_template/src/app.css` (Tailwind imports)
- [ ] Bump version to v0.13.0
- [ ] Update CHANGELOG.md
- [ ] Verify: `pnpm install && pnpm build` succeeds in the template dir

### Story D.b: v0.14.0 TypeScript Types and Curriculum Store [Planned]

Type definitions and Svelte stores for the frontend.

- [ ] Create `sveltekit_template/src/lib/types/index.ts` with all interfaces: `Curriculum`, `Module`, `Lesson`, `ContentBlock`, `QuizManifest`, `ExerciseContent`, `VisualizationContent`, progress types
- [ ] Create `sveltekit_template/src/lib/stores/curriculum.ts` — load `curriculum.json`, expose curriculum state and navigation helpers
- [ ] Bump version to v0.14.0
- [ ] Update CHANGELOG.md
- [ ] Verify: TypeScript compiles without errors

### Story D.c: v0.15.0 SQLite Progress Database [Planned]

In-browser SQLite for learner progress tracking.

- [ ] Create `sveltekit_template/src/lib/db/database.ts` — sql.js init, IndexedDB persistence, schema creation (tables: `lesson_progress`, `quiz_scores`, `exercise_status`)
- [ ] Create `sveltekit_template/src/lib/db/progress.ts` — CRUD: mark lesson complete, save quiz score, update exercise status, query module progress
- [ ] Create `sveltekit_template/src/lib/db/index.ts` (barrel export)
- [ ] Copy `sql-wasm.wasm` to `sveltekit_template/static/` via postinstall script
- [ ] Bump version to v0.15.0
- [ ] Update CHANGELOG.md
- [ ] Verify: database initializes on page load, CRUD operations work

### Story D.d: v0.16.0 Content Block Components [Planned]

Svelte components for rendering each content block type.

- [ ] Create `sveltekit_template/src/lib/components/TextBlock.svelte` — render HTML from markdown
- [ ] Create `sveltekit_template/src/lib/components/VideoBlock.svelte` — YouTube embed
- [ ] Create `sveltekit_template/src/lib/components/QuizBlock.svelte` — render quizazz manifest, scoring, write to SQLite
- [ ] Create `sveltekit_template/src/lib/components/ExerciseBlock.svelte` — render exercise content or stub placeholder
- [ ] Create `sveltekit_template/src/lib/components/VisualizationBlock.svelte` — render visualization or stub placeholder
- [ ] Create `sveltekit_template/src/lib/components/PlaceholderBlock.svelte` — generic "coming soon" placeholder
- [ ] Create `sveltekit_template/src/lib/components/ContentBlock.svelte` — dispatcher by block type
- [ ] Create `sveltekit_template/src/lib/utils/markdown.ts` — markdown-to-HTML utility
- [ ] Bump version to v0.16.0
- [ ] Update CHANGELOG.md

### Story D.e: v0.17.0 Navigation and Progress UI [Planned]

Navigation components and progress dashboard.

- [ ] Create `sveltekit_template/src/lib/components/ModuleList.svelte` — sidebar module navigation with progress indicators
- [ ] Create `sveltekit_template/src/lib/components/LessonList.svelte` — lesson list within a module
- [ ] Create `sveltekit_template/src/lib/components/Navigation.svelte` — prev/next lesson nav
- [ ] Create `sveltekit_template/src/lib/components/ProgressBar.svelte` — visual progress indicator
- [ ] Create `sveltekit_template/src/lib/components/ProgressDashboard.svelte` — per-module completion, quiz scores overview
- [ ] Bump version to v0.17.0
- [ ] Update CHANGELOG.md

### Story D.f: v0.18.0 Route Pages and Layout [Planned]

SvelteKit routes tying everything together.

- [ ] Create `sveltekit_template/src/routes/+layout.svelte` — app shell with sidebar navigation
- [ ] Create `sveltekit_template/src/routes/+page.svelte` — landing page / progress dashboard
- [ ] Create `sveltekit_template/src/routes/[module]/[lesson]/+page.svelte` — lesson page rendering content blocks via `LessonView.svelte`
- [ ] Create `sveltekit_template/src/lib/components/LessonView.svelte` — lesson content renderer
- [ ] Bump version to v0.18.0
- [ ] Update CHANGELOG.md
- [ ] Verify: full app builds, navigates modules/lessons, renders all block types

## Phase E: CLI Interface

### Story E.a: v0.19.0 CLI Build and Validate Commands [Planned]

Wire CLI to the pipeline orchestrator.

- [ ] Update `src/learningfoundry/cli.py`: implement `build` and `validate` subcommands
  - [ ] `build`: load config, call `run_build()`, handle errors with exit codes
  - [ ] `validate`: load config, call `run_validate()`, report result
  - [ ] Shared flags: `--config`, `--log-level`
- [ ] Create `tests/test_cli.py`
  - [ ] `build` produces output directory with fixture curriculum
  - [ ] `validate` reports OK for valid curriculum
  - [ ] `validate` reports errors for invalid curriculum
  - [ ] `--help` exits 0
  - [ ] Exit codes match spec (1=validation, 2=resolution, 3=generation, 4=config)
- [ ] Bump version to v0.19.0
- [ ] Update CHANGELOG.md

### Story E.b: v0.20.0 CLI Preview Command [Planned]

Build and serve locally.

- [ ] Implement `preview` subcommand in `cli.py`
  - [ ] Call `run_preview()` — build, `pnpm install`, start dev server
  - [ ] Accept `--port` flag (default 5173)
  - [ ] Print local URL
- [ ] Add test in `tests/test_cli.py` for preview (verify build step runs; dev server is an integration concern)
- [ ] Bump version to v0.20.0
- [ ] Update CHANGELOG.md

## Phase F: Testing and Quality

### Story F.a: v0.21.0 Test Suite Completion [Planned]

Fill any test gaps and ensure full coverage of high-value paths.

- [ ] Audit existing tests against tech-spec testing strategy
- [ ] Add any missing unit tests for edge cases (empty curriculum, all block types, large curriculum)
- [ ] Add integration test: full build with fixture curriculum containing all content block types
- [ ] Bump version to v0.21.0
- [ ] Update CHANGELOG.md
- [ ] Verify: `pyve test` passes all tests

### Story F.b: v0.22.0 Linting, Formatting, and Type Checking [Planned]

Enforce code quality tooling.

- [ ] Create `ruff.toml` or `[tool.ruff]` section in `pyproject.toml` with project-appropriate rules
- [ ] Configure mypy in `pyproject.toml` (`--strict`)
- [ ] Run `pyve testenv run ruff check .` — fix all issues
- [ ] Run `pyve testenv run mypy src/` — fix all type errors
- [ ] Bump version to v0.22.0
- [ ] Update CHANGELOG.md
- [ ] Verify: both pass cleanly

### Story F.c: SvelteKit Smoke Test [Planned]

Verify the generated app compiles end-to-end.

- [ ] Create a test fixture curriculum with all block types (text, video, quiz, exercise, visualization)
- [ ] Run `learningfoundry build` on the fixture
- [ ] Run `pnpm install && pnpm build` in the output directory
- [ ] Verify: build succeeds with no errors

## Phase G: Documentation and Release

### Story G.a: README and Changelog [Planned]

User-facing documentation.

- [ ] Write `README.md`: project description, installation, quick start, CLI usage, curriculum YAML format, development setup
- [ ] Create `CHANGELOG.md` with entries for v0.1.0 through current version
- [ ] Verify: README instructions work on a clean checkout

### Story G.b: v0.23.0 Final Polish and Release Prep [Planned]

Last checks before initial release.

- [ ] Review `pyproject.toml` metadata (description, classifiers, URLs)
- [ ] Verify `sveltekit_template/` is included in sdist/wheel builds
- [ ] Test `pip install` from built wheel in a clean venv
- [ ] Bump version to v0.23.0
- [ ] Update CHANGELOG.md
- [ ] Tag release as v0.23.0

## Phase H: CI/CD and Automation

### Story H.a: GitHub Actions — Lint and Test on Push [Planned]

Catch regressions on every push.

- [ ] Create `.github/workflows/ci.yml`
  - [ ] Trigger: push to `main`, pull requests
  - [ ] Matrix: Python 3.12, latest Ubuntu
  - [ ] Steps: checkout, install pyve, `pyve run pip install -e ".[dev]"`, `pyve testenv run ruff check .`, `pyve testenv run mypy src/`, `pyve test`
- [ ] Verify: workflow passes on push

### Story H.b: GitHub Actions — Coverage Badge [Planned]

Visible test coverage in the repo.

- [ ] Add `pytest-cov` to dev dependencies
- [ ] Update CI workflow to run `pyve test --cov=src/learningfoundry --cov-report=xml`
- [ ] Integrate with Codecov or Coveralls for dynamic badge
- [ ] Add coverage badge to `README.md`
- [ ] Verify: badge renders and updates on push


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
