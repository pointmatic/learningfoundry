# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
