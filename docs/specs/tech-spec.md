# tech-spec.md -- learningfoundry (Python 3.12 + SvelteKit)

This document defines **how** the `learningfoundry` project is built -- architecture, module layout, dependencies, data models, API signatures, and cross-cutting concerns.

For requirements and behavior, see `features.md`. For the implementation plan, see `stories.md`. For project-specific must-know facts (workflow rules, architecture quirks, hidden coupling), see `project-essentials.md` — `plan_tech_spec` populates it after this document is approved.

---

## Runtime & Tooling

| Concern | Tool | Version / Notes |
|---------|------|-----------------|
| **Language** | Python | 3.12.13 |
| **Environment manager** | pyve | venv backend; `.pyve/config` at project root |
| **Package manifest** | `pyproject.toml` | PEP 517/518, build backend: `hatchling` |
| **Package installer** | pip | Within venv managed by pyve |
| **Linter / formatter** | Ruff | Replaces flake8 + isort + black |
| **Type checker** | mypy | Strict mode (`--strict`) |
| **Test runner** | pytest | Standard |
| **Frontend framework** | SvelteKit | Latest stable; `@sveltejs/adapter-static` for static output |
| **Frontend language** | TypeScript | Strict mode |
| **Frontend styling** | Tailwind CSS 4.x | Utility-first |
| **Node runtime** | Node.js | Latest stable LTS |
| **Node package manager** | pnpm | Fast, workspace-aware |
| **Client-side DB** | sql.js (WASM) | SQLite compiled to WASM, persisted to IndexedDB |
| **Build tool (frontend)** | Vite | Via SvelteKit |

---

## Dependencies

### Python Runtime Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `pyyaml` | `>=6.0` | Curriculum YAML parsing |
| `pydantic` | `>=2.0` | Schema validation and data models for curriculum structure |
| `click` | `>=8.1` | CLI framework |

### Python Development Dependencies

| Package | Purpose |
|---------|---------|
| `pytest` | Test runner |
| `ruff` | Linting and formatting |
| `mypy` | Static type checking |

### Python Optional / Integration Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `quizazz-builder` | `>=0.1` | Quiz/assessment YAML → JSON manifest compilation (first-party) |

nbfoundry is not yet published. learningfoundry defines an `ExerciseProvider` protocol; a stub implementation ships for v1. The real nbfoundry integration will be added when nbfoundry is available as a package.

### SvelteKit App Runtime Dependencies (`package.json`)

| Package | Purpose |
|---------|---------|
| `svelte` | UI framework |
| `@sveltejs/kit` | App framework |
| `@sveltejs/adapter-static` | Static site generation |
| `sql.js` | SQLite WASM for client-side progress database |
| `lucide-svelte` | Icon library |

### SvelteKit App Dev Dependencies (`package.json`)

| Package | Purpose |
|---------|---------|
| `typescript` | Type checking |
| `tailwindcss` | Utility CSS framework |
| `@tailwindcss/vite` | Tailwind Vite plugin |
| `vitest` | Unit/integration testing |
| `eslint` | Linting |
| `prettier` | Code formatting |
| `prettier-plugin-svelte` | Svelte formatting support |

### System Dependencies

| Dependency | Required | Notes |
|------------|----------|-------|
| Node.js LTS | Yes | For SvelteKit build and preview |
| pnpm | Yes | Node package manager |
| pyve | Yes | Python environment management |

---

## Package Structure

```
learningfoundry/
├── pyproject.toml                          # Package metadata, dependencies, hatchling build
├── LICENSE                                 # Apache-2.0
├── README.md
├── .tool-versions                          # asdf/mise version pins (python 3.12.13)
├── .pyve/
│   └── config                              # pyve configuration (venv backend)
│
├── src/
│   └── learningfoundry/                    # Installable Python package
│       ├── __init__.py                     # Package version, public API exports
│       ├── py.typed                        # PEP 561 marker
│       ├── cli.py                          # Click CLI entry point (build, validate, preview)
│       ├── config.py                       # Settings model + config loading + precedence merging
│       ├── parser.py                       # YAML curriculum parser + version dispatch
│       ├── schema_v1.py                    # Pydantic models for curriculum YAML v1 schema
│       ├── resolver.py                     # Content resolution: markdown, video URLs, integrations
│       ├── asset_resolver.py               # Markdown image asset detection, hashing, and URL rewriting
│       ├── pipeline.py                     # Pipeline orchestrator: parse → resolve → generate
│       ├── generator.py                    # SvelteKit project generation from resolved curriculum
│       ├── integrations/
│       │   ├── __init__.py
│       │   ├── protocols.py                # QuizProvider, ExerciseProvider, and VisualizationProvider protocols
│       │   ├── quizazz.py                  # quizazz integration (delegates to quizazz_builder)
│       │   ├── nbfoundry_stub.py           # Stub ExerciseProvider for v1
│       │   └── d3foundry_stub.py           # Stub VisualizationProvider for v1
│       ├── exceptions.py                   # Project-specific exception hierarchy
│       └── logging_config.py              # Logging setup (stdlib logging, structured formatters)
│
├── sveltekit_template/                     # Bundled SvelteKit project template
│   ├── package.json                        # pnpm dependencies
│   ├── svelte.config.js                    # SvelteKit config with adapter-static
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── static/
│   │   └── sql-wasm.wasm                   # sql.js WASM binary
│   └── src/
│       ├── app.html                        # SvelteKit shell
│       ├── app.css                         # Tailwind imports + global styles
│       ├── lib/
│       │   ├── types/
│       │   │   └── index.ts                # TypeScript type definitions (curriculum, progress)
│       │   ├── db/
│       │   │   ├── index.ts                # Barrel export
│       │   │   ├── database.ts             # sql.js init, IndexedDB persistence, schema
│       │   │   └── progress.ts             # Progress CRUD: lesson completion, quiz scores, exercise status
│       │   ├── stores/
│       │   │   └── curriculum.ts           # Svelte stores for curriculum state and navigation
│       │   ├── components/
│       │   │   ├── ModuleList.svelte       # Module navigation sidebar
│       │   │   ├── LessonList.svelte       # Lesson list within a module
│       │   │   ├── LessonView.svelte       # Lesson content renderer (dispatches content blocks)
│       │   │   ├── ContentBlock.svelte     # Content block dispatcher (text, video, quiz, exercise, visualization)
│       │   │   ├── TextBlock.svelte        # Rendered markdown content (end-of-block sentinel drives `textcomplete`)
│       │   │   ├── VideoBlock.svelte       # YouTube embed
│       │   │   ├── QuizBlock.svelte        # Inline quiz (consumes quizazz manifest JSON)
│       │   │   ├── ExerciseBlock.svelte    # Model-training exercise (consumes nbfoundry output)
│       │   │   ├── VisualizationBlock.svelte # Data visualization (consumes d3foundry output)
│       │   │   ├── PlaceholderBlock.svelte # Placeholder for future interactive content
│       │   │   ├── ProgressDashboard.svelte # Per-module completion, quiz scores overview
│       │   │   ├── Navigation.svelte       # Prev/next lesson navigation
│       │   │   └── ProgressBar.svelte      # Visual progress indicator
│       │   └── utils/
│       │       └── markdown.ts             # Markdown-to-HTML rendering utility
│       └── routes/
│           ├── +layout.svelte              # App shell with sidebar navigation
│           ├── +page.svelte                # Landing / progress dashboard
│           └── [module]/
│               └── [lesson]/
│                   └── +page.svelte        # Lesson page rendering content blocks
│
├── tests/
│   ├── conftest.py                         # Shared fixtures (sample YAML, temp dirs)
│   ├── test_parser.py                      # YAML parsing: valid, missing version, bad version, dupes
│   ├── test_schema_v1.py                   # Pydantic model validation for v1 schema
│   ├── test_resolver.py                    # Content resolution: markdown, URLs, integration mocks
│   ├── test_pipeline.py                    # End-to-end pipeline orchestration
│   ├── test_generator.py                   # SvelteKit output structure verification
│   ├── test_config.py                      # Config precedence: CLI > file > defaults
│   ├── test_cli.py                         # CLI integration tests (build, validate, preview)
│   └── test_integrations/
│       ├── test_quizazz.py                 # quizazz integration (mocked builder calls)
│       ├── test_nbfoundry_stub.py          # Stub exercise provider behavior
│       └── test_d3foundry_stub.py          # Stub visualization provider behavior
│
└── docs/
    ├── project-guide/                      # project-guide configuration and templates
    └── specs/
        ├── concept.md
        ├── features.md
        ├── tech-spec.md                    # This document
        ├── stories.md
        └── project-essentials.md
```

---

## Filename Conventions

| File Type | Convention | Examples |
|-----------|------------|----------|
| **Documentation** (Markdown) | Hyphens | `tech-spec.md`, `getting-started.md` |
| **Workflow files** | Hyphens | `deploy-docs.yml`, `run-tests.yml` |
| **Python modules** | Underscores (PEP 8) | `schema_v1.py`, `logging_config.py` |
| **Python packages** | Underscores (PEP 8) | `learningfoundry/`, `integrations/` |
| **TypeScript / Svelte** | PascalCase (components), camelCase (modules) | `LessonView.svelte`, `database.ts` |
| **Configuration files** | Hyphens or dots | `pyproject.toml`, `.gitignore`, `svelte.config.js` |

---

## Key Component Design

### `cli.py` — Click CLI Entry Point

```python
import click

@click.group()
@click.option("--config", type=click.Path(exists=True), default=None,
              help="Path to config file (default: ~/.config/learningfoundry/config.yml)")
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
              default=None, help="Override log level")
def cli(config: str | None, log_level: str | None) -> None:
    """learningfoundry — turn a YAML curriculum into a SvelteKit learning app."""
    ...

@cli.command()
@click.argument("curriculum", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default="./build/",
              help="Output directory for the generated SvelteKit project")
def build(curriculum: str, output: str) -> None:
    """Run the full pipeline: parse → resolve → generate SvelteKit app."""
    ...

@cli.command()
@click.argument("curriculum", type=click.Path(exists=True))
def validate(curriculum: str) -> None:
    """Validate curriculum YAML without building."""
    ...

@cli.command()
@click.argument("curriculum", type=click.Path(exists=True))
@click.option("--port", type=int, default=5173, help="Dev server port")
@click.option("--output", "-o", type=click.Path(), default="./build/",
              help="Output directory for the generated SvelteKit project")
def preview(curriculum: str, port: int, output: str) -> None:
    """Build and launch a local dev server."""
    ...
```

### `config.py` — Settings Model

```python
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class LoggingConfig:
    level: str = "INFO"           # DEBUG | INFO | WARNING | ERROR
    output: str = "stdout"        # stdout | <file path>

@dataclass
class AppConfig:
    logging: LoggingConfig = field(default_factory=LoggingConfig)

def load_config(
    config_path: Path | None = None,
    cli_overrides: dict[str, str] | None = None,
) -> AppConfig:
    """
    Load configuration with precedence:
      1. CLI flags (cli_overrides)
      2. Config file (config_path or ~/.config/learningfoundry/config.yml)
      3. Built-in defaults (dataclass defaults)

    Raises ConfigError on malformed YAML.
    Logs warnings for unknown keys (forward-compatible).
    """
    ...
```

### `parser.py` — YAML Curriculum Parser

```python
from pathlib import Path
from learningfoundry.schema_v1 import CurriculumV1

def parse_curriculum(yaml_path: Path) -> CurriculumV1:
    """
    Parse and validate a curriculum YAML file.

    1. Load raw YAML via PyYAML.
    2. Extract top-level `version` field.
    3. Dispatch to the correct schema/parser based on major version.
    4. Validate via Pydantic model.
    5. Return typed, validated curriculum object.

    Raises:
        CurriculumVersionError: Missing or unsupported version.
        CurriculumValidationError: Schema validation failure (with field path detail).
    """
    ...

def _dispatch_parser(major_version: int):
    """Select parser/schema for the given major version.
    Currently supports: 1 → schema_v1.CurriculumV1.
    Raises CurriculumVersionError for unsupported versions."""
    ...
```

### `schema_v1.py` — Pydantic Models (Curriculum YAML v1)

```python
from pydantic import BaseModel, field_validator, model_validator
from pathlib import Path

class AssessmentRef(BaseModel):
    source: str                     # "quizazz"
    ref: str                        # Path to assessment YAML file

class TextBlock(BaseModel):
    type: str = "text"
    ref: str                        # Path to markdown file

class VideoBlock(BaseModel):
    type: str = "video"
    url: str
    provider: str = "youtube"              # Literal["youtube"] today; extend per player
    extensions: dict = {}                  # Player-specific (chapters, transcripts, …)

    @model_validator(mode="after")
    def validate_url_for_provider(self):
        """YouTube URL validation when provider is youtube."""
        ...

class QuizBlock(BaseModel):
    type: str = "quiz"
    source: str                     # "quizazz"
    ref: str                        # Path to quizazz assessment YAML
    pass_threshold: float = 0.0     # 0.0–1.0; minimum score ratio for completion

class ExerciseBlock(BaseModel):
    type: str = "exercise"
    source: str                     # "nbfoundry"
    ref: str                        # Path to nbfoundry exercise YAML

class VisualizationBlock(BaseModel):
    type: str = "visualization"
    source: str                     # "d3foundry"
    ref: str                        # Path to d3foundry visualization YAML

ContentBlock = TextBlock | VideoBlock | QuizBlock | ExerciseBlock | VisualizationBlock

class Lesson(BaseModel):
    id: str
    title: str
    unlock_module_on_complete: bool = False  # Unlock siblings + next module on complete
    content_blocks: list[ContentBlock]

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """IDs must be non-empty, lowercase, alphanumeric + hyphens."""
        ...

class Module(BaseModel):
    id: str
    title: str
    description: str = ""
    locked: bool | None = None      # None = inherit from locking config
    pre_assessment: AssessmentRef | None = None
    post_assessment: AssessmentRef | None = None
    lessons: list[Lesson]

    @model_validator(mode="after")
    def check_has_lessons(self) -> "Module":
        """Module must contain at least one lesson."""
        ...

class LockingConfig(BaseModel):
    sequential: bool = False        # Module N+1 requires module N complete
    lesson_sequential: bool = False # Lesson N+1 requires lesson N complete

class CurriculumDef(BaseModel):
    title: str
    description: str = ""
    locking: LockingConfig = LockingConfig()
    modules: list[Module]

    @model_validator(mode="after")
    def check_has_modules(self) -> "CurriculumDef":
        """Curriculum must contain at least one module."""
        ...

    @model_validator(mode="after")
    def check_unique_ids(self) -> "CurriculumDef":
        """All module IDs and lesson IDs must be unique."""
        ...

class CurriculumV1(BaseModel):
    version: str                    # Semver string, e.g. "1.0.0"
    curriculum: CurriculumDef
```

### `resolver.py` — Content Resolution

```python
from pathlib import Path
from learningfoundry.schema_v1 import CurriculumV1
from learningfoundry.integrations.protocols import QuizProvider, ExerciseProvider, VisualizationProvider

@dataclass
class ResolvedCurriculum:
    """Curriculum with all content references resolved to actual content."""
    version: str
    title: str
    description: str
    modules: list[ResolvedModule]
    assets: list[Asset] = field(default_factory=list)  # See asset_resolver.py

@dataclass
class ResolvedModule:
    id: str
    title: str
    description: str
    pre_assessment: dict | None      # Resolved quizazz manifest or None
    post_assessment: dict | None
    lessons: list[ResolvedLesson]

@dataclass
class ResolvedLesson:
    id: str
    title: str
    content_blocks: list[ResolvedContentBlock]

@dataclass
class ResolvedContentBlock:
    block_type: str                  # "text" | "video" | "quiz" | "exercise" | "visualization"
    content: str | dict              # HTML string, URL, or integration output dict

def resolve_curriculum(
    curriculum: CurriculumV1,
    base_dir: Path,
    quiz_provider: QuizProvider,
    exercise_provider: ExerciseProvider,
    visualization_provider: VisualizationProvider,
) -> ResolvedCurriculum:
    """
    Resolve all content references in the parsed curriculum.

    - text blocks: read markdown file from base_dir / ref, then call
      asset_resolver.resolve_markdown_assets() to detect image references,
      hash them, and rewrite the markdown to absolute /content/<hash>/
      URLs. Image asset records aggregate onto ResolvedCurriculum.assets
      (deduped globally by content hash).
    - video blocks: validate YouTube URL, pass through
    - quiz blocks: delegate to quiz_provider
    - exercise blocks: delegate to exercise_provider
    - visualization blocks: delegate to visualization_provider

    Raises ContentResolutionError on missing files (markdown or referenced
    images), invalid URLs, or integration errors. Error messages always
    include the block location (module / lesson / block index).
    """
    ...
```

### `asset_resolver.py` — Markdown Image Asset Resolution

Pure module that scans a lesson's markdown for image references and rewrites
them to absolute SvelteKit-compatible URLs. Designed to be called once per
text block by `resolver.py`; emits `Asset` records that the generator
consumes to copy files into the output `static/` directory.

```python
from pathlib import Path
from dataclasses import dataclass

@dataclass(frozen=True)
class Asset:
    """A single asset that the generator must copy into the project."""
    source: Path           # Absolute path to the source file on disk
    dest_relative: str     # "content/<sha256[:12]>/<basename>" (forward-slash, URL-safe)

    @property
    def url_path(self) -> str:
        """The leading-slash URL the rewritten markdown references."""
        return "/" + self.dest_relative

def resolve_markdown_assets(
    markdown: str,
    markdown_path: Path,
) -> tuple[str, list[Asset]]:
    """
    Find every image reference in `markdown` and resolve it.

    Match forms:
      - Markdown:  `![alt](url)`, `![alt](url "title")`
      - HTML:      `<img src="url">` or `<img src='url'>`

    Passthrough rules (no resolution, no Asset record):
      - http://, https://, // (protocol-relative)
      - leading / (already a SvelteKit static URL)
      - data:, mailto:, tel: URIs
      - References inside fenced code blocks (``` or ~~~)

    On-disk resolution:
      - Relative paths resolve against `markdown_path.parent`.
      - Query (`?cache=1`) and fragment (`#anchor`) are stripped before lookup.
      - Missing file → ContentResolutionError with the markdown path in
        the message; resolver.py wraps with the lesson location prefix.
      - SHA-256 of file bytes; first 12 hex chars become the dest dir.
      - Multiple references to the same source file → one Asset record,
        all references rewritten to the same URL.

    Returns (rewritten_markdown, deduped_assets_in_first-seen_order).
    """
    ...
```

### `integrations/protocols.py` — Provider Protocols

```python
from typing import Protocol
from pathlib import Path

class QuizProvider(Protocol):
    def compile_assessment(self, ref_path: Path, base_dir: Path) -> dict:
        """
        Compile an assessment YAML file into a renderable manifest dict.
        Returns the quizazz manifest structure (questions, nav tree).
        Raises IntegrationError on parse/validation failure.
        """
        ...

class ExerciseProvider(Protocol):
    def compile_exercise(self, ref_path: Path, base_dir: Path) -> dict:
        """
        Compile an exercise YAML file into a renderable exercise dict.
        Returns exercise content (instructions, code scaffolding, expected outputs).
        Raises IntegrationError on parse/validation failure.
        """
        ...

class VisualizationProvider(Protocol):
    def compile_visualization(self, ref_path: Path, base_dir: Path) -> dict:
        """
        Compile a visualization definition into a renderable artifact dict.
        Returns visualization content (image data, HTML, or component config).
        Raises IntegrationError on parse/validation failure.
        """
        ...
```

### `integrations/quizazz.py` — quizazz Integration

```python
from pathlib import Path
from learningfoundry.integrations.protocols import QuizProvider

class QuizazzProvider:
    """
    QuizProvider implementation backed by quizazz_builder.

    Delegates to quizazz_builder.validator.validate_file() and
    quizazz_builder.compiler.compile_quiz() to produce a manifest dict
    from a single assessment YAML file.
    """

    def compile_assessment(self, ref_path: Path, base_dir: Path) -> dict:
        """
        1. Resolve ref_path relative to base_dir.
        2. Call quizazz_builder.validator.validate_file(resolved_path).
        3. Call quizazz_builder.compiler.compile_quiz() with validated output.
        4. Return manifest dict.
        Raises IntegrationError wrapping any quizazz ValidationError.
        """
        ...
```

### `integrations/nbfoundry_stub.py` — Stub Exercise Provider

```python
from pathlib import Path
from learningfoundry.integrations.protocols import ExerciseProvider

class NbfoundryStub:
    """
    Stub ExerciseProvider for v1.

    Returns a placeholder exercise dict with the ref path and a
    "coming soon" message. The real nbfoundry integration will
    generate Marimo applications for interactive model-training exercises.
    """

    def compile_exercise(self, ref_path: Path, base_dir: Path) -> dict:
        return {
            "type": "exercise",
            "source": "nbfoundry",
            "ref": str(ref_path),
            "status": "stub",
            "title": f"Exercise: {ref_path.stem}",
            "instructions": f"<p>Exercise placeholder for <code>{ref_path}</code>. "
                            "nbfoundry integration pending.</p>",
            "sections": [],
            "expected_outputs": [],
            "hints": [],
            "environment": None,
        }
```

### `integrations/d3foundry_stub.py` — Stub Visualization Provider

```python
from pathlib import Path
from learningfoundry.integrations.protocols import VisualizationProvider

class D3foundryStub:
    """
    Stub VisualizationProvider for v1.

    Returns a placeholder visualization dict. The real d3foundry
    integration will generate Matplotlib images, D3.js interactive
    visualizations, or brokered artifacts (CNN Explainer, etc.).
    """

    def compile_visualization(self, ref_path: Path, base_dir: Path) -> dict:
        return {
            "type": "visualization",
            "source": "d3foundry",
            "ref": str(ref_path),
            "status": "stub",
            "title": f"Visualization: {ref_path.stem}",
            "caption": "",
            "render_type": "image",
            "content": "",
            "content_type": "image/svg+xml",
            "alt_text": f"Placeholder for {ref_path}",
        }
```

### `pipeline.py` — Pipeline Orchestrator

```python
from pathlib import Path
from learningfoundry.config import AppConfig
from learningfoundry.resolver import ResolvedCurriculum

def run_build(
    curriculum_path: Path,
    output_dir: Path,
    config: AppConfig,
) -> None:
    """
    Full build pipeline:
      1. Parse curriculum YAML (parser.parse_curriculum)
      2. Resolve content references (resolver.resolve_curriculum)
      3. Generate SvelteKit project (generator.generate_app)

    Logs progress at each stage. Fails fast on first error.
    """
    ...

def run_validate(
    curriculum_path: Path,
    config: AppConfig,
) -> None:
    """
    Validation-only pipeline:
      1. Parse curriculum YAML
      2. Resolve content references (validates file existence, URLs, integration refs)
      3. Report "Curriculum is valid." or error details.
    """
    ...

def run_preview(
    curriculum_path: Path,
    output_dir: Path,
    port: int,
    config: AppConfig,
) -> None:
    """
    Build + preview pipeline:
      1. Run full build pipeline
      2. Run `pnpm install` in the generated SvelteKit project
      3. Start `pnpm run dev --port <port>` as a subprocess
      4. Print local URL and stream server output
    """
    ...
```

### `generator.py` — SvelteKit Project Generation

```python
from pathlib import Path
from learningfoundry.resolver import ResolvedCurriculum

def generate_app(
    curriculum: ResolvedCurriculum,
    output_dir: Path,
) -> None:
    """
    Generate a complete SvelteKit project from the resolved curriculum.

    1. Copy the bundled sveltekit_template/ to output_dir, atomically (write
       to sibling temp dir, then rename). State directories listed in
       _PRESERVED_PATHS are moved from the existing output (if any) into the
       fresh template copy before the swap, so install/build artefacts and
       previously-copied image assets survive a rebuild without having to
       re-run pnpm install. The current preserved set:
         - node_modules
         - pnpm-lock.yaml
         - build
         - .svelte-kit
         - static/content   (image assets copied by step 3)
    2. Write curriculum.json into output_dir/static/, containing the full
       resolved curriculum structure (modules, lessons, content blocks with
       resolved content). The `assets` field on ResolvedCurriculum is
       intentionally stripped — it carries on-disk Path objects (not JSON
       serialisable) and is consumed only by the next step.
    3. Copy each Asset record from ResolvedCurriculum.assets into
       output_dir/static/<dest_relative>. Idempotent: a destination file
       whose size matches the source is left untouched (the content-hashed
       path makes matching size a strong identity signal).

    If output_dir exists, the log message is INFO-level and notes which
    state directories are being preserved.
    """
    ...
```

### `exceptions.py` — Exception Hierarchy

```python
class LearningFoundryError(Exception):
    """Base exception for all learningfoundry errors."""

class ConfigError(LearningFoundryError):
    """Config file is malformed or contains invalid values."""

class CurriculumVersionError(LearningFoundryError):
    """Missing or unsupported curriculum YAML version."""

class CurriculumValidationError(LearningFoundryError):
    """Curriculum YAML fails schema validation.
    Includes field path and validation detail from Pydantic."""

class ContentResolutionError(LearningFoundryError):
    """Content reference cannot be resolved.
    Includes block location (module/lesson/block index) and specific cause."""

class IntegrationError(LearningFoundryError):
    """An integration library (quizazz, nbfoundry, d3foundry) returned an error.
    Wraps the library's original error with block location context."""

class GenerationError(LearningFoundryError):
    """SvelteKit project generation failed."""
```

---

## Data Models

### Curriculum YAML Schema (v1)

See `schema_v1.py` above for the full Pydantic model. The YAML structure matches the example in `features.md`:

```yaml
version: "1.0.0"
curriculum:
  title: "D802 Deep Learning Essentials"
  description: "A hands-on curriculum covering deep learning fundamentals."
  modules:
    - id: mod-01
      title: "Introduction to Neural Networks"
      description: "..."
      pre_assessment:
        source: quizazz
        ref: assessments/mod-01-pre.yml
      lessons:
        - id: lesson-01
          title: "What is a Neural Network?"
          content_blocks:
            - type: text
              ref: content/mod-01/lesson-01.md
            - type: video
              url: "https://www.youtube.com/watch?v=..."
            - type: quiz
              source: quizazz
              ref: assessments/mod-01-lesson-01-quiz.yml
            - type: exercise
              source: nbfoundry
              ref: exercises/mod-01-exercise-01.yml
            - type: visualization
              source: d3foundry
              ref: visualizations/mod-01-cnn-architecture.yml
      post_assessment:
        source: quizazz
        ref: assessments/mod-01-post.yml
```

### Resolved Curriculum (in-memory)

The `ResolvedCurriculum` dataclass tree (see `resolver.py` above) is serialized to `curriculum.json` in the generated SvelteKit project for the frontend to consume.

In addition to the module/lesson/content tree, `ResolvedCurriculum` carries an `assets: list[Asset]` field — the deduped union of every image asset referenced by any text block's markdown. Each `Asset` is a `(source: Path, dest_relative: str)` pair where `dest_relative = "content/<sha256[:12]>/<basename>"`. The list is consumed by `generator.generate_app()` to copy files into `output_dir/static/`; it is **stripped before serialisation to curriculum.json** because it carries `Path` objects (not JSON-serialisable) and the SvelteKit frontend only ever needs the rewritten URL embedded in the lesson markdown — never the original source path.

### curriculum.json (generated, consumed by SvelteKit)

```json
{
  "version": "1.0.0",
  "title": "D802 Deep Learning Essentials",
  "description": "...",
  "modules": [
    {
      "id": "mod-01",
      "title": "Introduction to Neural Networks",
      "description": "...",
      "pre_assessment": { "...quizazz manifest..." },
      "post_assessment": { "...quizazz manifest..." },
      "lessons": [
        {
          "id": "lesson-01",
          "title": "What is a Neural Network?",
          "content_blocks": [
            { "type": "text", "content": "<p>Rendered HTML from markdown...</p>" },
            { "type": "video", "content": "https://www.youtube.com/watch?v=..." },
            { "type": "quiz", "content": { "...quizazz manifest..." } },
            { "type": "exercise", "content": { "...nbfoundry output..." } },
            { "type": "visualization", "content": { "...d3foundry output..." } }
          ]
        }
      ]
    }
  ]
}
```

### SQLite Progress Schema (in-browser)

```sql
CREATE TABLE IF NOT EXISTS lesson_progress (
  lesson_id     TEXT PRIMARY KEY,
  module_id     TEXT NOT NULL,
  completed     INTEGER NOT NULL DEFAULT 0,   -- 0 = incomplete, 1 = complete
  completed_at  INTEGER                        -- Unix timestamp, NULL if incomplete
);

CREATE TABLE IF NOT EXISTS quiz_scores (
  quiz_ref      TEXT PRIMARY KEY,              -- Assessment ref path (unique per quiz)
  module_id     TEXT NOT NULL,
  quiz_type     TEXT NOT NULL,                 -- "pre" | "post" | "inline"
  score         INTEGER NOT NULL DEFAULT 0,
  max_score     INTEGER NOT NULL DEFAULT 0,
  completed_at  INTEGER NOT NULL               -- Unix timestamp
);

CREATE TABLE IF NOT EXISTS exercise_status (
  exercise_ref  TEXT PRIMARY KEY,              -- Exercise ref path
  module_id     TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'not_started',  -- "not_started" | "in_progress" | "completed"
  updated_at    INTEGER NOT NULL               -- Unix timestamp
);
```

### SvelteKit TypeScript Types (`lib/types/index.ts`)

```typescript
export interface Curriculum {
  version: string;
  title: string;
  description: string;
  modules: Module[];
}

export interface Module {
  id: string;
  title: string;
  description: string;
  pre_assessment: QuizManifest | null;
  post_assessment: QuizManifest | null;
  lessons: Lesson[];
}

export interface Lesson {
  id: string;
  title: string;
  content_blocks: ContentBlock[];
}

export interface ContentBlock {
  type: "text" | "video" | "quiz" | "exercise" | "visualization" | "placeholder";
  content: string | QuizManifest | ExerciseContent | VisualizationContent;
}

export interface QuizManifest {
  // Matches quizazz compiled manifest structure
  quizName: string;
  tree: NavNode[];
  questions: Question[];
}

export interface ExerciseContent {
  type: "exercise";
  source: string;
  ref: string;
  status: "ready" | "stub";
  title: string;
  instructions: string;
  sections: ExerciseSection[];
  expected_outputs: ExpectedOutput[];
  hints: string[];
  environment: ExerciseEnvironment | null;
}

export interface ExerciseSection {
  title: string;
  description: string;
  code: string;
  editable: boolean;
}

export interface ExpectedOutput {
  description: string;
  type: "image" | "text" | "table";
  content: string;
}

export interface ExerciseEnvironment {
  python_version: string;
  dependencies: string[];
  setup_instructions: string;
}

export interface VisualizationContent {
  type: "visualization";
  source: string;
  ref: string;
  status: "ready" | "stub";
  title: string;
  caption: string;
  render_type: "image" | "html" | "svelte_component";
  content: string;           // base64 image, HTML string, or component ID
  content_type: string;      // MIME type (e.g., "image/svg+xml", "text/html")
  alt_text: string;
}

export interface LessonProgress {
  lessonId: string;
  moduleId: string;
  completed: boolean;
  completedAt: number | null;
}

export interface QuizScore {
  quizRef: string;
  moduleId: string;
  quizType: "pre" | "post" | "inline";
  score: number;
  maxScore: number;
  completedAt: number;
}

export interface ExerciseStatus {
  exerciseRef: string;
  moduleId: string;
  status: "not_started" | "in_progress" | "completed";
  updatedAt: number;
}

export interface ModuleProgress {
  moduleId: string;
  lessonsCompleted: number;
  lessonsTotal: number;
  percentComplete: number;
  preAssessmentScore: QuizScore | null;
  postAssessmentScore: QuizScore | null;
}
```

---

## Configuration

### Precedence (highest to lowest)

1. CLI flags (e.g., `--log-level DEBUG`)
2. Global config file (`~/.config/learningfoundry/config.yml`)
3. Built-in defaults (dataclass defaults in `config.py`)

### Global Config Schema (v1)

```yaml
# ~/.config/learningfoundry/config.yml
logging:
  level: INFO          # DEBUG | INFO | WARNING | ERROR
  output: stdout       # stdout | <file path>
```

Unknown keys are ignored with a warning logged (forward-compatible).

### Settings Model

```python
@dataclass
class LoggingConfig:
    level: str = "INFO"
    output: str = "stdout"

@dataclass
class AppConfig:
    logging: LoggingConfig = field(default_factory=LoggingConfig)
```

---

## CLI Design

### Subcommands

| Command | Arguments | Description |
|---------|-----------|-------------|
| `learningfoundry build <curriculum.yml>` | `--output`, `--log-level`, `--config` | Full pipeline: parse → resolve → generate SvelteKit app |
| `learningfoundry validate <curriculum.yml>` | `--log-level`, `--config` | Schema + reference validation only |
| `learningfoundry preview <curriculum.yml>` | `--port`, `--output`, `--log-level`, `--config` | Build + local dev server |

### Shared Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--config` | Path | `~/.config/learningfoundry/config.yml` | Config file path |
| `--log-level` | Choice | From config or `INFO` | Override log level |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Curriculum validation error (schema, missing files, bad version) |
| `2` | Content resolution error (integration failure, missing content) |
| `3` | Generation error (SvelteKit build failure) |
| `4` | Configuration error (malformed config file) |

---

## Cross-Cutting Concerns

### Error Handling

- **Fail-fast**: Pipeline exits on the first error with a clear, actionable message.
- **Error context**: Every error includes the source location (file path, module/lesson/block index) and a description of what went wrong and how to fix it.
- **Exception hierarchy**: All custom exceptions inherit from `LearningFoundryError`. CLI catches this base class, prints the formatted message, and exits with the appropriate code.
- **Integration errors**: Wrapped in `IntegrationError` with block location context prepended to the library's original message.

### Logging

- Standard library `logging` module with structured formatters.
- Default: `INFO` level to `stdout`.
- Configurable via global config file and `--log-level` CLI flag.
- Pipeline stages log progress at `INFO` (e.g., "Parsing curriculum...", "Resolving content for module mod-01...", "Generating SvelteKit project...").
- Content resolution details at `DEBUG`.
- Warnings for non-fatal issues (empty markdown file, unknown config keys, output directory overwrite).

### YAML Versioning

- Every curriculum YAML must include a top-level `version` field (semver string).
- The parser extracts the major version and dispatches to the corresponding schema module (`schema_v1.py`).
- Currently supported: major version `1`.
- New major versions add a new `schema_vN.py` module and a dispatch entry in `parser.py`.

### WASM Binary Handling

The `sql-wasm.wasm` file is bundled in the SvelteKit template's `static/` directory. It is copied from `node_modules/sql.js/dist/sql-wasm.wasm` during `pnpm install` via a postinstall script. The frontend initializes sql.js with `locateFile: (file) => \`/${file}\`` to load from the static root.

### Atomic Output

`generator.generate_app()` writes to a temporary directory first, then moves it to the final `output_dir` atomically. If `output_dir` already exists, it is replaced (with a warning logged). This prevents partial output on failure.

---

## Performance Implementation

No specific performance targets for v1. The pipeline is synchronous and single-threaded.

- **YAML parsing**: PyYAML + Pydantic validation — fast for typical curriculum sizes (10–20 modules).
- **Content resolution**: Sequential file reads and integration calls. No parallelism needed at expected scale.
- **SvelteKit generation**: File copy + JSON serialization. Bottleneck is `pnpm install` on first build.
- **Preview**: Delegates to SvelteKit's Vite dev server, which handles HMR and incremental builds.

Performance optimization is deferred until real workloads identify bottlenecks.

---

## Testing Strategy

### Unit Tests

| Module | What is tested |
|--------|----------------|
| `test_parser.py` | Valid curriculum parsing, missing version, unsupported version, malformed YAML |
| `test_schema_v1.py` | Pydantic model validation: required fields, content block types, ID uniqueness, URL format, lesson/module minimums |
| `test_resolver.py` | Markdown loading, YouTube URL validation, empty markdown warning, integration error propagation (mocked providers) |
| `test_config.py` | Precedence: CLI > config file > defaults; malformed config; unknown keys warning |
| `test_integrations/test_quizazz.py` | QuizazzProvider delegates correctly to quizazz_builder (mocked); error wrapping |
| `test_integrations/test_nbfoundry_stub.py` | Stub returns placeholder dict with correct structure |
| `test_integrations/test_d3foundry_stub.py` | Stub returns placeholder visualization dict with correct structure |

### Integration Tests

| Test | What is tested |
|------|----------------|
| `test_pipeline.py` | End-to-end build with a small fixture curriculum (2 modules, 3 lessons). Verifies output directory structure. |
| `test_cli.py` | CLI invocation: `build` produces output, `validate` reports OK or errors, `--help` exits 0. Uses a fixture curriculum YAML and mock content files. |
| `test_generator.py` | Generated SvelteKit project contains expected files (`package.json`, `curriculum.json`, route files). Does **not** run `pnpm build` — that is a smoke test. |

### Smoke Tests

- Generated SvelteKit project compiles without errors (`pnpm install && pnpm build` in CI).
- Fixture curriculum with all content block types builds end-to-end.

---

## Packaging and Distribution

### Package Metadata (`pyproject.toml`)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "learningfoundry"
version = "0.1.0"
description = "Turn a YAML curriculum definition into a deployable SvelteKit learning application"
readme = "README.md"
license = "Apache-2.0"
requires-python = "==3.12.*"
authors = [{ name = "Pointmatic" }]
dependencies = [
    "pyyaml>=6.0",
    "pydantic>=2.0",
    "click>=8.1",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "ruff",
    "mypy",
]
quizazz = [
    "quizazz-builder>=0.1",
]
nbfoundry = [
    "nbfoundry>=0.1",
]
d3foundry = [
    "d3foundry>=0.1",
]

[project.scripts]
learningfoundry = "learningfoundry.cli:cli"

[tool.hatch.build.targets.sdist]
include = ["src/learningfoundry", "sveltekit_template"]

[tool.hatch.build.targets.wheel]
packages = ["src/learningfoundry"]
# sveltekit_template is included as package data
```

### Package Data

The `sveltekit_template/` directory is included in the distribution as package data so that the generator can copy it to the output directory at runtime.

### Registry

Published to **PyPI** as `learningfoundry`.

### Installation

```bash
pip install learningfoundry                # core
pip install learningfoundry[quizazz]       # with quizazz integration
pip install learningfoundry[nbfoundry]     # with nbfoundry integration (future)
pip install learningfoundry[d3foundry]     # with d3foundry integration (future)
```

### Console Script

`learningfoundry` → `learningfoundry.cli:cli` (Click entry point).
