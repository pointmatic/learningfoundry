# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
