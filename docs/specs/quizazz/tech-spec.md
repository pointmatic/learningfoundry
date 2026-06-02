# tech-spec.md — Quizazz (TypeScript / SvelteKit + Python)

This document defines **how** the `quizazz` project is built -- architecture, module layout, dependencies, data models, API signatures, and cross-cutting concerns.

For requirements and behavior, see [`features.md`](features.md). For the implementation plan, see [`stories.md`](stories.md). For project-specific must-know facts (workflow rules, architecture quirks, hidden coupling), see [`project-essentials.md`](project-essentials.md) — `plan_tech_spec` populates it after this document is approved. For the workflow steps tailored to the current mode (cycle steps, approval gates, conventions), see [`docs/project-guide/go.md`](../project-guide/go.md) — re-read it whenever the mode changes or after context compaction.

---

## Runtime & Tooling

| Concern | Choice | Notes |
|---------|--------|-------|
| **App framework** | SvelteKit 2.x on Svelte 5 | Runes syntax (`$state`, `$derived`, `$props`); static SPA via `@sveltejs/adapter-static` |
| **Language (app)** | TypeScript 5.x | Strict mode enabled |
| **Styling** | Tailwind CSS 4.x | Utility-first; `@tailwindcss/vite` plugin; minimal custom CSS |
| **Icons** | `lucide-svelte` | Hand-rolled components otherwise; no UI framework |
| **Client-side DB** | sql.js (WASM) | SQLite compiled to WASM, persisted to IndexedDB |
| **Build tool (app)** | Vite 7 (via SvelteKit) | Standard SvelteKit toolchain |
| **Component packaging** | `@sveltejs/package` + `@tailwindcss/cli` | `@sveltejs/package` emits the JS / `.svelte` source into `dist/`; `@tailwindcss/cli` emits the precompiled `dist/styles.css` bundle (sub-exported as `./styles.css`). Together they produce the published `@pointmatic/quizazz` npm package for UC-3 |
| **Node package manager** | pnpm 10+ | Workspace-aware, fast |
| **Linter / formatter (JS/TS)** | ESLint + Prettier | SvelteKit defaults; `prettier-plugin-svelte` |
| **Test runner (JS/TS)** | Vitest 4 | Vite-native; `@testing-library/svelte` for component tests |
| **Python runtime** | Python 3.12+ | Used only in `python/` for YAML validation and manifest compilation |
| **Python packaging backend** | `setuptools >= 75` | `pyproject.toml`-driven; editable install via `pip install -e ./builder` |
| **Python package manager** | pip inside a venv | Venv managed by Pyve (see project-essentials for the canonical invocation form) |
| **Linter / formatter (Python)** | Ruff | Replaces flake8/isort/black |
| **Test runner (Python)** | pytest 8 | Standard |

---

## Data Flow

Two code trees, one content pipeline. `python/` contains the `quizazz` Python package (validator + compiler + CLI + library API). `app/` contains the SvelteKit SPA. They don't share a runtime — they chain at build time via compiled JSON manifests.

**UC-1 / UC-2 (disk-based, CLI-driven):**

```
data/<quiz>/*.yaml
  → [quizazz generate]          (python/ — validate + compile)
  → app/src/lib/data/*.json     (checked-in; glob-imported by Vite)
  → [quizazz build → pnpm --dir app build]
  → app/build/                  (deployable static site)
  → [quizazz run]               (local http.server, optional)
```

The `quizazz` CLI orchestrates every step; each step can also be run standalone (`pnpm --dir app build` directly, `vitest`, etc.).

**UC-3 (in-memory, library API):**

```
host YAML
  → compile_assessment(path, base_dir)   (python/ — no disk writes)
  → dict                                  (host owns JSON emission / bundling)
```

The host framework calls `compile_assessment` at *its own* build time. No subprocess, no temp files, no SvelteKit involvement on the Python side. The SvelteKit artefact for UC-3 is the separate `@pointmatic/quizazz` npm package (Phase L).

**Directory roles at a glance:**

| Directory | Role | Produces |
|-----------|------|----------|
| [data/](data/) | YAML content source of truth | — |
| [python/](python/) | Python package (`quizazz`): validator, compiler, CLI, library API | Compiled manifests → `app/src/lib/data/*.json`; dicts → host callers (UC-3) |
| [app/](app/) | SvelteKit SPA + `@pointmatic/quizazz` component library | `app/build/` static site (UC-1/UC-2); `app/dist/` npm package (UC-3, Phase L) |
| [docs/](docs/) | Specs, plans, project-guide templates | — |

---

## Dependencies

### App runtime (`app/package.json`)

| Package | Purpose |
|---------|---------|
| `svelte` ^5 | UI framework (runes mode) |
| `@sveltejs/kit` ^2 | App framework |
| `@sveltejs/adapter-static` ^3 | Static site generation |
| `@sveltejs/vite-plugin-svelte` ^6 | Svelte Vite integration |
| `sql.js` ^1 | SQLite WASM for client-side database |
| `lucide-svelte` ^0.5 | Icon library |
| `vite` ^7 | Underlying build tool |

### App dev (`app/package.json`)

| Package | Purpose |
|---------|---------|
| `typescript` ^5 | Type checking |
| `tailwindcss` ^4 + `@tailwindcss/vite` ^4 | Utility CSS for the in-tree app build |
| `@tailwindcss/cli` ^4 | Build-time emitter for `dist/styles.css` (the precompiled bundle published with `@pointmatic/quizazz`); driven by `app/scripts/build-styles.mjs` during `pnpm package` |
| `vitest` ^4 | Unit / component / integration testing |
| `@testing-library/svelte` ^5 | Component-level test utilities |
| `@types/sql.js` ^1 | Type definitions for sql.js |
| `svelte-check` ^4 | Svelte type-check pass |
| `eslint` ^10, `prettier` ^3, `prettier-plugin-svelte` ^3 | Linting / formatting |
| `@sveltejs/package` | (enabled via SvelteKit) component-library emit for npm |

### Builder runtime (`python/pyproject.toml`)

| Package | Purpose |
|---------|---------|
| `pyyaml >= 6` | YAML parsing |
| `pydantic >= 2` | Schema validation and models |

### Builder dev (`python/pyproject.toml` `[project.optional-dependencies].dev`)

| Package | Purpose |
|---------|---------|
| `pytest >= 8` | Testing |
| `ruff >= 0.11` | Linting / formatting |

---

## Package Structure

```
quizazz/
├── LICENSE                                    # Apache-2.0
├── README.md                                  # Project overview, setup, usage
├── install.sh                                 # Developer install helper
├── data/
│   ├── quiz/                                  # Default quiz (ships with repo)
│   │   ├── sample.yaml
│   │   └── advanced/
│   │       └── *.yaml
│   ├── aws-ml-specialty-exam/                 # Additional bundled quiz
│   │   └── *.yaml
│   └── <other-quiz>/                          # User-created quizzes
│       └── *.yaml
├── app/
│   ├── package.json                           # Publishes @pointmatic/quizazz (UC-3)
│   ├── pnpm-workspace.yaml
│   ├── svelte.config.js                       # adapter-static + package config
│   ├── vite.config.ts
│   ├── vitest.config.ts
│   ├── tsconfig.json
│   ├── static/
│   │   └── favicon.png                        # (sql-wasm.wasm is bundled by Vite via `?url` import; not checked in)
│   ├── src/
│   │   ├── app.html
│   │   ├── app.css                            # Tailwind imports + globals
│   │   ├── lib/
│   │   │   ├── data/
│   │   │   │   ├── *.json                     # Compiled quiz manifests (glob-imported)
│   │   │   │   └── index.ts                   # import.meta.glob → manifests[]
│   │   │   ├── db/
│   │   │   │   ├── index.ts                   # Barrel
│   │   │   │   ├── database.ts                # sql.js init, per-quiz IndexedDB persistence
│   │   │   │   └── scores.ts                  # Score CRUD + session answer recording
│   │   │   ├── engine/
│   │   │   │   ├── lifecycle.ts               # Quiz lifecycle (start/submit/retake/review/elapsedMs)
│   │   │   │   ├── selection.ts               # Weighted random selection
│   │   │   │   ├── presentation.ts            # Answer draw + shuffle + labeling
│   │   │   │   ├── scoring.ts                 # Point calculation
│   │   │   │   └── mastery.ts                 # Per-node score aggregation
│   │   │   ├── stores/
│   │   │   │   ├── quiz.ts                    # quizSession, viewMode, reviewIndex
│   │   │   │   └── manifest.ts                # activeManifest + derived questions/navTree/allTags
│   │   │   ├── types/
│   │   │   │   └── index.ts                   # Shared TypeScript types
│   │   │   ├── utils/
│   │   │   │   ├── random.ts                  # Shuffle, weighted sampling
│   │   │   │   ├── validate-manifest.ts       # Runtime upload validator
│   │   │   │   └── format.ts                  # Formatting helpers (elapsed time, percentages)
│   │   │   ├── components/
│   │   │   │   ├── QuizChooser.svelte         # UC-2 chooser
│   │   │   │   ├── ManifestUpload.svelte      # UC-2 runtime upload control
│   │   │   │   ├── NavigationTree.svelte
│   │   │   │   ├── ConfigView.svelte
│   │   │   │   ├── QuizView.svelte
│   │   │   │   ├── AnsweredQuestionsView.svelte
│   │   │   │   ├── ReviewView.svelte
│   │   │   │   ├── SummaryView.svelte
│   │   │   │   └── ProgressBar.svelte
│   │   │   └── embed/
│   │   │       ├── QuizBlock.svelte           # UC-3 embeddable component
│   │   │       ├── index.ts                   # Public package entry for @pointmatic/quizazz
│   │   │       └── styles.css                 # Source for the precompiled dist/styles.css bundle
│   │   └── routes/
│   │       ├── +layout.svelte
│   │       ├── +layout.ts                     # prerender = true, ssr = false
│   │       └── +page.svelte                   # Single-page SPA; all UC-1/UC-2 views
│   └── tests/
│       ├── db/
│       ├── engine/
│       ├── stores/
│       ├── utils/
│       ├── integration/
│       └── embed/                             # QuizBlock component tests
├── python/
│   ├── pyproject.toml                         # Publishes quizazz to PyPI
│   ├── src/
│   │   └── quizazz/
│   │       ├── __init__.py                    # Public API: compile_assessment, validate_assessment, ValidationError
│   │       ├── __main__.py                    # Thin entry for `python -m quizazz` (delegates to cli.main)
│   │       ├── cli.py                         # Unified CLI: generate / build / run / build --standalone
│   │       ├── models.py                      # Pydantic models (Answer, AnswerSet, Question, SubtopicGroup, QuizFile)
│   │       ├── validator.py                   # File + directory validation; ValidationError
│   │       ├── compiler.py                    # QuizFile → manifest compilation
│   │       └── manifest.py                    # Nav-tree construction from directory hierarchy
│   └── tests/
│       ├── test_models.py
│       ├── test_validator.py
│       ├── test_compiler.py
│       ├── test_manifest.py
│       ├── test_cli.py
│       └── test_api.py                        # UC-3 public-API tests
└── docs/
    ├── project-guide/                         # go.md + templates (managed by project-guide)
    └── specs/
        ├── concept.md
        ├── features.md
        ├── tech-spec.md
        ├── stories.md
        ├── learningfoundry/
        │   ├── consumer-dependency-spec.md
        │   └── vendor-pushback-recommendations.md
        ├── llm_question_generation.md
        ├── llm_question_generation_manual.md
        └── .archive/                            # deprecated / historical specs (e.g., multi_quiz_features.md)
```

---

## Filename Conventions

| File Type | Convention | Examples |
|-----------|------------|----------|
| **Markdown docs** | Hyphens, lowercase | `tech-spec.md`, `learningfoundry/consumer-dependency-spec.md` |
| **YAML content** | Hyphens, lowercase | `domain1-data-engineering.yaml`, `topic-a.yaml` |
| **Python modules / packages** | Underscores (PEP 8) | `quizazz/`, `validate_manifest.py` |
| **Svelte components** | PascalCase | `QuizBlock.svelte`, `NavigationTree.svelte` |
| **TypeScript modules** | kebab-case for files; camelCase for exports | `validate-manifest.ts`, `activeManifest` |
| **Config files** | Dotted / lowercase | `pyproject.toml`, `svelte.config.js`, `.gitignore` |
| **Compiled manifests** | Quiz directory name, lowercase | `aws-ml-specialty-exam.json` |
| **SQLite / IndexedDB** | `quizazz-<quiz-name>` | `quizazz-aws-ml-specialty-exam` |

---

## Key Component Design

### Builder — `quizazz.models`

Pydantic v2 models define and validate the YAML schema. All models are frozen to the shape described in [`features.md`](features.md) Inputs section.

```python
class Answer(BaseModel):
    text: str                      # non-empty
    explanation: str               # non-empty

class AnswerSet(BaseModel):
    correct: list[Answer]          # >= 1
    partially_correct: list[Answer]  # >= 1
    incorrect: list[Answer]        # >= 1
    ridiculous: list[Answer]       # >= 1
    # @model_validator: sum >= 5

class Question(BaseModel):
    question: str                  # non-empty
    tags: list[str] | None = None  # @field_validator: lowercase, non-empty strings
    answers: AnswerSet

class SubtopicGroup(BaseModel):
    subtopic: str                  # non-empty
    questions: list[Question]      # >= 1

class QuizFile(BaseModel):
    menu_name: str                 # non-empty
    menu_description: str = ""
    quiz_description: str = ""
    questions: list[Question | SubtopicGroup]  # >= 1
```

`QuestionBank(RootModel[list[Question]])` is retained as a deprecated legacy type for transitional code paths.

### Builder — `quizazz.validator`

```python
class ValidationError(Exception):
    """Raised on any YAML schema violation.

    Attributes:
        file_path: Path
        message: str
        detail: dict | None   # question index, field name, etc.
    """

def validate_file(path: Path) -> QuizFile:
    """Parse + validate a single YAML file. Raises ValidationError on any violation."""

def validate_quiz_directory(quiz_dir: Path) -> list[tuple[Path, QuizFile]]:
    """Recursively validate all *.yaml files in a quiz directory.
    Returns a list of (relative_path, QuizFile) tuples preserving hierarchy."""
```

### Builder — `quizazz.compiler`

```python
def compile_quiz(
    validated: list[tuple[Path, QuizFile]],
    quiz_name: str,
    output_dir: Path
) -> None:
    """Emit <output_dir>/<quiz_name>.json (CLI mode) containing the full manifest."""

def compile_quiz_to_dict(
    validated: list[tuple[Path, QuizFile]],
    quiz_name: str
) -> dict:
    """Shared core — returns the manifest dict without writing. Used by both the
    CLI (via compile_quiz) and the public library API (compile_assessment)."""
```

Stable question IDs are derived via SHA-256 of the question text (short-hashed for readability).

### Builder — `quizazz.manifest`

```python
def build_navigation_tree(
    validated: list[tuple[Path, QuizFile]]
) -> list[dict]:
    """Build the nav-tree array from directory structure + file metadata.
    Directory nodes (type='directory'), topic nodes (type='topic'),
    subtopic nodes (type='subtopic'). Each node carries questionIds for
    per-node mastery aggregation."""
```

### Builder — `quizazz.cli`

Unified CLI dispatch. Subcommands:

```
quizazz generate --input <dir> [--output <dir>] [--all]
quizazz build [--output <dir>] [--standalone <quiz-name>]
quizazz run [--port N] [--output <dir>]
```

- `generate` runs `validate_quiz_directory` → `compile_quiz`.
- `build` shells out to `pnpm --dir app build` after (optionally) staging manifests.
  - In `--standalone <name>` mode, before invoking pnpm the CLI copies only `<output>/<name>.json` into `app/src/lib/data/`, temporarily relocating other manifests, and sets an env var `QUIZAZZ_STANDALONE=<name>` that the app uses to hide chooser / upload UI.
- `run` ensures the app is built, then serves `app/build/` via `http.server` and opens `http://localhost:<port>`.

### Builder — `quizazz.__init__` (public library API, UC-3)

```python
# quizazz/__init__.py

from .validator import ValidationError
from .api import compile_assessment, validate_assessment

__all__ = ["compile_assessment", "validate_assessment", "ValidationError", "__version__"]
```

Behind a thin `api.py` module:

```python
def compile_assessment(yaml_path: Path | str, base_dir: Path | str) -> dict:
    """Validate + compile a single assessment YAML into a manifest dict.

    Raises:
        ValidationError with .file_path, .message, .detail populated.
    """
    full = Path(base_dir) / yaml_path
    quiz_file = validate_file(full)  # raises ValidationError
    validated = [(Path(yaml_path), quiz_file)]
    quiz_name = Path(yaml_path).stem
    return compile_quiz_to_dict(validated, quiz_name)

def validate_assessment(yaml_path: Path | str, base_dir: Path | str) -> list[str]:
    """Validate without compiling. Returns an empty list on success or a list of
    human-readable error strings (one per violation)."""
    try:
        validate_file(Path(base_dir) / yaml_path)
    except ValidationError as exc:
        return [str(exc)]
    return []
```

**Key constraints (enforced by API design):**
- Synchronous. No async, no I/O beyond reading the specified YAML file.
- No disk writes, no server startup, no subprocesses.
- Returns plain dicts (JSON-serializable) — the host owns JSON emission.

### App — `lib/types/index.ts`

```typescript
export type AnswerCategory = "correct" | "partially_correct" | "incorrect" | "ridiculous";

export interface Answer {
  text: string;
  explanation: string;
  category: AnswerCategory;
}

export interface Question {
  id: string;
  question: string;
  tags: string[];
  answers: Answer[];
  topicId: string;
  subtopic: string | null;
}

export type NavNodeType = "directory" | "topic" | "subtopic";

export interface NavNode {
  id: string;
  label: string;
  description: string;
  type: NavNodeType;
  questionIds: string[];
  children: NavNode[];
}

export interface QuizManifest {
  quizName: string;
  tree: NavNode[];
  questions: Question[];
}

export interface QuizConfig {
  questionCount: number;
  answerCount: 3 | 4 | 5;
  selectedTags: string[];
  selectedNodeIds: string[];
}

export interface PresentedAnswer extends Answer {
  label: string;                   // "a" .. "e"
}

export interface QuizQuestion {
  question: Question;
  presentedAnswers: PresentedAnswer[];
  selectedLabel: string | null;    // tentative (deferred scoring)
  submittedLabel: string | null;   // committed on submit
  elapsedMs: number;               // per-question timer snapshot
}

export interface QuizSession {
  config: QuizConfig;
  questions: QuizQuestion[];
  currentIndex: number;
  completed: boolean;
}

export interface QuestionScore {
  questionId: string;
  cumulativeScore: number;
}

export interface QuizCompleteEvent {
  quizRef: string;
  score: number;
  maxScore: number;
  questionCount: number;
}
```

### App — `lib/data/index.ts`

```typescript
import type { QuizManifest } from '$lib/types';

const modules = import.meta.glob<QuizManifest>('./*.json', {
  eager: true,
  import: 'default'
});

export const manifests: QuizManifest[] = Object.values(modules).map(m => m as QuizManifest);
```

Every `*.json` dropped into `app/src/lib/data/` by `quizazz generate` is bundled at build time. The `manifests` array drives chooser behavior: a single manifest auto-selects and bypasses the chooser; multiple manifests render `QuizChooser`.

### App — `lib/stores/manifest.ts`

```typescript
export const activeManifest = writable<QuizManifest | null>(null);
export const questions = derived(activeManifest, ($m) => $m?.questions ?? []);
export const navTree  = derived(activeManifest, ($m) => $m?.tree ?? []);
export const allTags  = derived(questions, ($q) => [...new Set($q.flatMap(q => q.tags))].sort());
```

### App — `lib/stores/quiz.ts`

```typescript
export const quizSession = writable<QuizSession | null>(null);

export type ViewMode =
  | "chooser"            // UC-2 multi-quiz entry
  | "nav"                // navigation tree
  | "config"             // config screen
  | "quiz"               // active quiz
  | "quiz-answered"      // mid-quiz answered-list
  | "quiz-review"        // mid-quiz review of one question
  | "summary"            // post-quiz summary
  | "review";            // post-quiz drill-down

export const viewMode = writable<ViewMode>("chooser");
export const reviewIndex = writable<number | null>(null);

export const currentQuestion = derived(quizSession, ($s) =>
  $s ? $s.questions[$s.currentIndex] : null
);

export const progress = derived(quizSession, ($s) => {
  if (!$s) return { current: 0, total: 0, percent: 0 };
  const answered = $s.questions.filter(q => q.submittedLabel !== null).length;
  return {
    current: answered,
    total: $s.questions.length,
    percent: Math.round((answered / $s.questions.length) * 100)
  };
});
```

### App — `lib/engine/selection.ts`

```typescript
export function selectQuestions(
  pool: Question[],
  scores: QuestionScore[],
  count: number,
  tagFilter: string[]
): Question[];
```

- Applies `tagFilter` (OR logic; empty = no filter).
- Weight formula: `weight = maxScore - score + 1` (guarantees ≥ 1).
- Weighted sampling **without replacement** — draw count ≤ pool size, else pool-exhausted.

### App — `lib/engine/presentation.ts`

```typescript
export function presentAnswers(question: Question, answerCount: 3 | 4 | 5): PresentedAnswer[];
```

1. Random 1 from `correct`.
2. Random (answerCount − 1) from union of `partially_correct | incorrect | ridiculous`.
3. Shuffle; assign labels `a`..`e`.

### App — `lib/engine/scoring.ts`

```typescript
export const SCORE_MAP: Record<AnswerCategory, number> = {
  correct: 1,
  partially_correct: -2,
  incorrect: -5,
  ridiculous: -10
};

export function scoreAnswer(category: AnswerCategory): number;
```

### App — `lib/engine/mastery.ts`

```typescript
export interface MasteryScore {
  total: number;
  positive: number;                 // questions with cumulativeScore > 0
  percent: number;                  // 0..100, rounded
}

export function computeMastery(questionIds: string[], scores: QuestionScore[]): MasteryScore;
```

### App — `lib/engine/lifecycle.ts`

Pure-TS quiz lifecycle functions operating on the stores. Key responsibilities:

- `setNavNodes(nodes)` — stash the active nav tree for later scoping.
- `startQuiz(config, allQuestions, scores, db, quizName)` — build a `QuizSession`, initialize `questionStartTime`, transition `viewMode` to `"quiz"`.
- `submitAnswer(db, selectedLabel)` — commit `selectedLabel` → `submittedLabel`, persist score, advance `currentIndex`, update `frontierIndex`, stamp `elapsedMs`.
- `retakeQuiz()` / `newQuiz()` / `quitQuiz()` — post-quiz transitions.
- `showAnsweredQuestions()` / `editAnsweredQuestion(idx)` / `backToQuiz()` — mid-quiz review navigation.
- `reviewQuestion(idx)` / `backToSummary()` / `reviewPrev()` / `reviewNext()` — post-quiz drill-down carousel.
- `getFrontierIndex()` / `getQuestionStartTime()` — accessors used by views for UI state derivation.

Timer: `questionStartTime` resets when a question is first presented; `elapsedMs` is snapshotted into the `QuizQuestion` on submit or on mid-quiz view transitions.

### App — `lib/utils/validate-manifest.ts`

```typescript
export type ValidationResult =
  | { ok: true; manifest: QuizManifest }
  | { ok: false; error: string };

export function validateManifest(data: unknown): ValidationResult;   // shape-check
export function parseAndValidate(text: string): ValidationResult;    // JSON.parse + validate
```

Used by `ManifestUpload` to reject malformed files client-side with a human-readable error. The validator performs a shape check (required top-level fields, array types, per-question `id`/`question`/`answers` presence) — full schema enforcement happens at build time (Python).

### App — Components (core)

| Component | View | Role |
|-----------|------|------|
| `QuizChooser` | `chooser` | Lists pre-bundled + session-uploaded manifests; includes `ManifestUpload` |
| `ManifestUpload` | (embedded in chooser) | File input + client-side validation; on success, passes a validated manifest up |
| `NavigationTree` | `nav` | Tree with mastery badges, selection state |
| `ConfigView` | `config` | Tag toggles, question-count slider, answer-count radios, Start button |
| `QuizView` | `quiz` | Current question, answer selection, timer, progress, submit |
| `AnsweredQuestionsView` | `quiz-answered` | List of previously submitted questions |
| `ReviewView` | `quiz-review`, `review` | Single-question detail with carousel |
| `SummaryView` | `summary` | Score %, per-question outcomes, Retake/Start/Quit |
| `ProgressBar` | (in QuizView) | "Question N of M" + percent bar |

### App — `lib/embed/QuizBlock.svelte` (UC-3)

The public component for host frameworks. Self-contained wrapper around the core engine and views.

```svelte
<script lang="ts">
  import type { QuizManifest, QuizCompleteEvent } from '$lib/types';

  interface Props {
    manifest: QuizManifest;
    quizRef: string;
    oncomplete?: (e: QuizCompleteEvent) => void;
  }

  let { manifest, quizRef, oncomplete }: Props = $props();
  // Mount: init per-quiz DB (keyed by manifest.quizName), set nav nodes,
  //        start the quiz immediately over the full manifest question set.
  // On submit of the last question: compute aggregate, call oncomplete({...}).
</script>
```

**Design notes:**
- Uses the same engine modules (`selection`, `presentation`, `scoring`, `lifecycle`) and the same per-quiz IndexedDB scheme as UC-1/UC-2 — isolation is preserved by keying on `manifest.quizName`.
- Runs the whole manifest as the question set (no topic/subtopic scoping, no tag filter, no config screen). `answerCount` defaults to 4; overriding it is Future Vision.
- Renders `QuizView` + `AnsweredQuestionsView` + `ReviewView` + `SummaryView` internally; no nav or chooser UI.
- Keyboard handlers are scoped to the component's root element via `on:keydown` on a `tabindex="0"` container rather than `window` listeners. This prevents leakage of `a`–`e`, `Enter`, `Escape`, `←`/`→` into the host.
- Emits `complete` via the `oncomplete` callback prop (Svelte 5 convention) and, for compatibility with hosts using the classic event dispatch pattern, dispatches a `CustomEvent('complete', { detail })` on the root element.
- Retake reshuffles the answer order but keeps the same question set (same per-question DB updates apply).
- Ships a precompiled `dist/styles.css` (~13 KB minified) alongside the JS — Tailwind utilities authored against `<QuizBlock>` and the views it reaches (`QuizView`, `ReviewView`, `AnsweredQuestionsView`, `SummaryView`, `ProgressBar`) are pre-emitted at package time so hosts get a polished default look without their own Tailwind setup. The bundle skips Tailwind's preflight/base layer (no global resets), keeps the theme + utilities layers only, and is opt-in via the host's explicit `import '@pointmatic/quizazz/styles.css'` (no `<svelte:head>` auto-injection).

### App — `src/lib/embed/index.ts` and `./styles.css` sub-export

```typescript
export { default as QuizBlock } from './QuizBlock.svelte';
export type {
  QuizManifest,
  QuizCompleteEvent,
  AnswerCategory,
  Answer,
  Question,
  NavNode
} from '$lib/types';
```

This barrel is the public entry for the `@pointmatic/quizazz` npm package. Hosts also import the precompiled stylesheet via the `./styles.css` sub-export:

```ts
import { QuizBlock } from '@pointmatic/quizazz';
import '@pointmatic/quizazz/styles.css';
```

The CSS bundle is built by `app/scripts/build-styles.mjs` using `@tailwindcss/cli`; its source is `src/lib/embed/styles.css` (theme + utilities, `source(none)` + explicit `@source` directives for the embed-reachable component files only).

### App — `src/routes/+page.svelte`

Single-page orchestrator for UC-1 / UC-2. Manages top-level state (`db`, `scores`, `selectedNodeIds`, `filteredQuestions`, `uploadedManifests`). On mount:

- If `manifests.length === 1` AND no standalone-disabled upload UI → auto-select and go to `nav`.
- Else → go to `chooser`.

Honors a `QUIZAZZ_STANDALONE` build-time env var (exposed via Vite `import.meta.env`) that, when set, hides `ManifestUpload` and auto-selects the named manifest.

---

## Data Models

### Compiled JSON Manifest (UC-1 / UC-2 / UC-3)

```json
{
  "quizName": "module-4-pre-assessment",
  "tree": [
    {
      "id": "module-4-pre-assessment",
      "label": "Module 4 Pre-Assessment",
      "description": "CNN fundamentals",
      "type": "topic",
      "questionIds": ["a1b2…", "c3d4…", "e5f6…"],
      "children": []
    }
  ],
  "questions": [
    {
      "id": "a1b2…",
      "question": "What does a convolutional layer compute?",
      "tags": ["cnn"],
      "topicId": "module-4-pre-assessment",
      "subtopic": null,
      "answers": [
        { "text": "...", "explanation": "...", "category": "correct" },
        { "text": "...", "explanation": "...", "category": "partially_correct" },
        { "text": "...", "explanation": "...", "category": "incorrect" },
        { "text": "...", "explanation": "...", "category": "ridiculous" },
        { "text": "...", "explanation": "...", "category": "ridiculous" }
      ]
    }
  ]
}
```

The manifest shape is identical regardless of how it is produced (CLI or `compile_assessment`) and consumed (SPA bundle or `<QuizBlock>` prop). **This shape is the versioned contract** between `quizazz` and `@pointmatic/quizazz` — breaking changes require a major bump in both.

### SQLite schema (per-quiz IndexedDB)

```sql
CREATE TABLE IF NOT EXISTS question_scores (
  question_id      TEXT PRIMARY KEY,
  cumulative_score INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS session_answers (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id        TEXT NOT NULL,
  question_id       TEXT NOT NULL,
  selected_category TEXT NOT NULL,
  points            INTEGER NOT NULL,
  timestamp         INTEGER NOT NULL
);
```

Schema is identical across all quizzes; isolation is achieved at the IndexedDB-database level (`quizazz-<quizName>`). `session_answers` is written per-submit and read only during the current session for mid-quiz/post-quiz review.

---

## Configuration

### Build-time (UC-1 / UC-2)

| Setting | Default | Source |
|---------|---------|--------|
| Input quiz directory | `data/quiz/` | `quizazz generate --input` |
| Data root (batch) | `data/` | `quizazz generate --all --input` |
| Manifest output dir | `app/src/lib/data/` | `quizazz generate --output` |
| App build output | `app/build/` | `quizazz build --output` |
| Standalone target | (unset) | `quizazz build --standalone <name>` → sets `QUIZAZZ_STANDALONE` env for Vite |
| Local server port | `8000` | `quizazz run --port` |

### Build-time (UC-3)

Hosts call `compile_assessment(yaml_path, base_dir)` directly. No Quizazz-level config file is required on the host side.

### Runtime

All UC-1 / UC-2 runtime configuration is through the in-app screens (nav, config). UC-3 runtime input is confined to the `manifest` + `quizRef` props. No environment variables, no config files, no server.

Runtime precedence is trivial (there is effectively only one source in each mode), so no precedence table is warranted.

---

## CLI Design

Console script `quizazz` is installed by `quizazz` (PyPI), registered in `[project.scripts]` as `quizazz = "quizazz.cli:main"`.

### Subcommands

| Subcommand | Purpose | Key flags |
|------------|---------|-----------|
| `generate` | YAML → manifest JSON | `--input`, `--output`, `--all` |
| `build` | `pnpm --dir app build`, with optional standalone staging | `--output`, `--standalone <quiz-name>` |
| `run` | Ensure build, serve `app/build/`, open browser | `--port`, `--output` |

Only `quizazz` is registered as a console script. `python -m quizazz` also works via a thin `__main__.py` that delegates to `cli.main`.

### Shared behavior

- `--version` on the root parser prints `quizazz <__version__>`.
- `--help` is supported on every subcommand.
- Exit code **0** on success, **1** on any error (validation, missing `pnpm`, non-existent directories, build-subprocess failure).
- Validation errors are printed to stderr with a `Validation error:` prefix and the offending file/question/detail.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | User error (missing dir, no quizzes found, unknown subcommand) |
| 1 | Validation failure (a non-zero exit with stderr `Validation error: …`) |
| 1 | Build-subprocess failure (pnpm build returned non-zero) |

---

## Cross-Cutting Concerns

### Database persistence strategy

1. On app load (or on `<QuizBlock>` mount): resolve quiz name from the active manifest; attempt restore from IndexedDB keyed `quizazz-<quizName>`.
2. If missing or corrupt → create fresh sql.js DB, apply schema, seed `question_scores` at 0 for every manifest question ID.
3. After every score update → persist via sql.js → IndexedDB write (synchronous semantics; ≤1 write/second in normal use, so no debouncing).
4. Retake does **not** reset the DB; scores accumulate.
5. Per-quiz isolation: one IndexedDB database per `quizName`. Cross-quiz interference is structurally impossible.

### Error handling

| Layer | Strategy |
|-------|----------|
| Builder CLI | Print `Validation error: <detail>` to stderr, exit 1. `ValidationError` (raised by validator) carries file path + message + detail. |
| Library API (`compile_assessment`) | Raise `ValidationError(file_path, message, detail)`. No swallowing. |
| App build | Missing `app/src/lib/data/*.json` → Vite import error (build fails). |
| App runtime (DB) | `try/catch` around sql.js; unrecoverable error → user-friendly banner with "Reset Database" action that drops and recreates the IndexedDB entry. |
| App runtime (manifest upload) | Reject via `validate-manifest` with a human-readable message; no state change. |
| `<QuizBlock>` | Same DB error policy; fatal errors escalate to a slotted error state rather than crashing the host. |

### Keyboard interaction map

| Key | View | Action |
|-----|------|--------|
| `a`–`e` | `quiz` | Select corresponding answer (tentative) |
| `Enter` | `quiz` (answer selected) | Submit answer |
| `Enter` | `config` (valid) | Start quiz |
| `Escape` | `quiz` (has answered ≥ 1) | Open answered-questions list |
| `Escape` | `quiz-answered` / `quiz-review` | Return to current question |
| `Escape` | `review` | Return to summary |
| `←` / `→` | `review`, `quiz-review` | Navigate review carousel |

**UC-3 scoping**: `<QuizBlock>` binds keydown to its root element (tabindex=0), not `window`, so host keyboard shortcuts remain unaffected.

### WASM binary handling

- `app/src/lib/db/database.ts` imports the WASM via Vite's `?url` asset-import pattern: `import wasmUrl from 'sql.js/dist/sql-wasm.wasm?url';`. Vite resolves the import at host build time, emits the file into the build output (e.g. `_app/immutable/assets/sql-wasm-<hash>.wasm` for SvelteKit), and rewrites `wasmUrl` to that hashed URL. sql.js is then initialized with `locateFile: () => wasmUrl`, and a HEAD precheck against `wasmUrl` surfaces a `WasmAssetMissingError` if the asset is unreachable.
- This applies uniformly to UC-1/UC-2 (the standalone SvelteKit build) and UC-3 (the `<QuizBlock>` npm package): hosts of `@pointmatic/quizazz` get the WASM bundled into their own build output automatically, with no `cp` / postinstall step. The previously-checked-in `app/static/sql-wasm.wasm` and any postinstall copy script have been removed.
- Hosts must still disable SSR on any route that mounts `<QuizBlock>` (`export const ssr = false;` in `+page.ts` or `+layout.ts`) — sql.js and IndexedDB are browser-only, so a server-side render attempt throws during initialization. Documented in the package README under "SvelteKit host setup".

### Standalone build mechanics (UC-1)

`quizazz build --standalone <quiz-name>`:

1. Verify `<output>/<quiz-name>.json` exists.
2. Move all `app/src/lib/data/*.json` except the target to a temp directory.
3. Set `QUIZAZZ_STANDALONE=<quiz-name>` in the environment passed to `pnpm --dir app build`.
4. The app reads `import.meta.env.VITE_QUIZAZZ_STANDALONE` (Vite exposes env vars with `VITE_` prefix; the CLI sets both unprefixed and prefixed variants). When set, `+page.svelte` hides `ManifestUpload`, auto-selects the single manifest, and the chooser is never entered.
5. On completion, restore the moved manifests so the source tree is unchanged.
6. On failure at any step, restore manifests and surface the error.

### Library API path resolution (UC-3)

- `base_dir` is resolved to an absolute path with `Path.resolve()` at entry.
- `yaml_path` is joined as `base_dir / yaml_path` and must resolve to a path strictly under `base_dir` (defensive check) to prevent accidental path escapes when the host is composing paths from user-authored curricula.
- No symlink following is disabled, but out-of-tree resolution raises `ValidationError`.

### Embedded component isolation (UC-3)

- `<QuizBlock>` never touches `window.location`, `history`, cookies, or `fetch`. All DB activity is confined to its per-quiz IndexedDB.
- The component authors styles with Tailwind, but ships them as a precompiled `dist/styles.css` bundle (built by `@tailwindcss/cli` against an embed-reachable-only source list — no project-wide Tailwind footprint). The bundle skips Tailwind's preflight/base layer entirely, so importing it does not restyle host elements outside `<QuizBlock>`. Hosts pull it via the `./styles.css` sub-export (`import '@pointmatic/quizazz/styles.css'`); host-side Tailwind utilities, when present, layer additively via the cascade. CSS custom properties (`--quizazz-*`) remain the universal theming surface on top of either setup.
- The manifest is treated as read-only; the component never mutates the prop.

---

## Performance Implementation

| Concern | Approach |
|---------|----------|
| **Question-bank size** | Designed for tens to low hundreds per quiz. No pagination, no virtualization. |
| **sql.js operations** | Synchronous; at this scale, full DB reads/writes complete in single-digit ms. |
| **IndexedDB persistence** | Flush after each score update. Write frequency ≤ 1/sec → no batching needed. |
| **Manifest bundling** | `import.meta.glob` with `eager: true` inlines manifests at build time; zero runtime fetch cost. Bundle size grows ~linearly with question count. |
| **Mastery aggregation** | Recomputed on demand from the in-memory score array; `O(Q)` per node; trivially cached per component render if needed. |
| **Library API latency** | `compile_assessment` parses + validates + compiles in < 100 ms for typical pre/post assessments (3–5 questions). Hosts may call it in tight loops during build. |
| **Weighted selection** | Linear scan over the pool; `O(N)` per draw, `O(N·count)` total — fine up to thousands of questions. |
| **Concurrency** | Single-threaded runtime (browser). Python library API is synchronous by contract. |

---

## Testing Strategy

### Python (`python/tests/`)

| Test file | Covers |
|-----------|--------|
| `test_models.py` | Pydantic validation: every field rule; category minimums; total ≥ 5; tag normalization; subtopic rules; QuizFile metadata |
| `test_validator.py` | YAML parsing; valid/malformed files; missing files; recursive directory validation; `ValidationError` attributes populated (file_path, message, detail) |
| `test_compiler.py` | Manifest output: structure, stable IDs (hash determinism), category flattening, `topicId` + `subtopic` references |
| `test_manifest.py` | Nav-tree construction: directory hierarchy, topic/subtopic nesting, `questionIds` correctness at each node |
| `test_cli.py` | `quizazz generate` single + batch; `quizazz build --standalone <name>` staging logic (using a tmp data dir); exit codes and stderr messages |
| `test_api.py` (**UC-3**) | `compile_assessment` happy path (valid YAML → manifest dict matching schema); `compile_assessment` raises `ValidationError` with file_path/message/detail; `validate_assessment` returns `[]` for valid; returns error strings for invalid; path-escape guard |

### TypeScript (`app/tests/`)

| Test file | Covers |
|-----------|--------|
| `db/scores.test.ts` | Score CRUD; cumulative behavior; seed behavior; missing-question handling |
| `engine/selection.test.ts` | Weighted distribution (statistical over N iterations); nonzero probability guarantee; tag filtering; pool-exhaustion fallback |
| `engine/presentation.test.ts` | Exactly one correct answer per presentation; total count matches config; labels assigned correctly; shuffling |
| `engine/scoring.test.ts` | Category → points mapping |
| `engine/mastery.test.ts` | Per-node aggregation; rounding |
| `engine/lifecycle.test.ts` | Full flow nav → config → quiz → summary → review; deferred scoring (change selection before submit does not record a score); mid-quiz review does not mutate progress |
| `stores/*.test.ts` | `quizSession`, `viewMode`, `reviewIndex`, `progress` derived-store behavior |
| `utils/random.test.ts` | Shuffle uniformity; weighted-pick correctness |
| `utils/validate-manifest.test.ts` | Accept valid manifest; reject every malformed shape with a readable message; JSON parse failure path |
| `integration/edge-cases.test.ts` | 1-question quiz; max-count quiz; answer counts 3/4/5; uniform scores; all-negative scores |
| `integration/navigation.test.ts` | Nav-tree rendering, node selection, question-pool scoping |
| `integration/tags.test.ts` | Tag OR filter correctness; dynamic pool-size update |
| `embed/QuizBlock.test.ts` (**UC-3**) | Renders a manifest; keyboard events don't bubble past the root; all-correct run → emits `complete({quizRef, score: N, maxScore: N, questionCount: N})`; retake resets presentation but accumulates cumulative scores |

---

## Packaging and Distribution

### Python — `quizazz` on PyPI

- **Package name**: `quizazz`
- **Importable as**: `quizazz`
- **License**: Apache-2.0 (set in `pyproject.toml` `[project].license`)
- **Build backend**: `setuptools >= 75` via `pyproject.toml`
- **Console scripts**:
  - `quizazz = "quizazz.cli:main"` (sole entry point; `python -m quizazz` also works via `__main__.py`)
- **Public API** (importable):
  ```python
  from quizazz import compile_assessment, validate_assessment, ValidationError
  ```
- **Optional extras**: `[dev]` → pytest, ruff.
- **Python classifiers**: 3.12+, OS Independent, Topic :: Education :: Testing.
- **Release**: `python -m build` → `twine upload`. Host frameworks pin with `quizazz >= <manifest-schema-version>`.

### npm — `@pointmatic/quizazz`

- **Package name**: `@pointmatic/quizazz`
- **Publish scope**: `@pointmatic` (npm org)
- **Published from**: `app/` workspace via `@sveltejs/package` (`pnpm --dir app package`).
- **`package.json` exports**:
  ```json
  {
    "name": "@pointmatic/quizazz",
    "version": "<matches the single project version>",
    "license": "Apache-2.0",
    "files": ["dist", "!dist/**/*.test.*", "!dist/**/*.spec.*"],
    "exports": {
      ".": {
        "types": "./dist/embed/index.d.ts",
        "svelte": "./dist/embed/index.js",
        "default": "./dist/embed/index.js"
      },
      "./styles.css": "./dist/styles.css"
    },
    "peerDependencies": {
      "svelte": "^5"
    },
    "dependencies": {
      "sql.js": "^1"
    }
  }
  ```
- **Package contents** (emitted into `dist/` by `pnpm --dir app package`, which chains `svelte-package` → `scripts/build-styles.mjs` → `scripts/clean-dist.mjs`):
  - `embed/QuizBlock.svelte`
  - `embed/index.js` + `.d.ts`
  - Internal engine / db / utils modules the component needs.
  - **`styles.css`** — precompiled stylesheet emitted by `@tailwindcss/cli` from `src/lib/embed/styles.css` (theme + utilities, `source(none)` + explicit `@source` for embed-reachable Svelte files only, no preflight). Sub-exported as `./styles.css`.
  - **Not included**: `routes/`, chooser/upload components, standalone build machinery, the `embed/styles.css` source (stripped post-build by `clean-dist.mjs` so the only published stylesheet is the compiled `dist/styles.css`).
- **Peer expectations**: host provides a Svelte 5 runtime, runs a Vite-based build (so `?url` asset imports resolve — SvelteKit and standard Vite hosts qualify), disables SSR on routes that mount `<QuizBlock>`, and imports `@pointmatic/quizazz/styles.css` for the default look. The sql.js WASM asset is bundled into the host's build output automatically via Vite's `?url` import — no host-side WASM copy is required. `sql.js` is a runtime dependency of the package; hosts do not declare it directly. All documented in the package README.

### Installation methods

| Audience | Install |
|----------|---------|
| Repo dev (all workspaces) | `pip install -e ./builder[dev]` + `pnpm --dir app install` |
| CLI user (UC-1/UC-2) | `pip install quizazz` → `quizazz …` |
| Host-framework author (UC-3, Python side) | `pip install quizazz` (optional extra in host's own `pyproject.toml`) |
| Host-framework author (UC-3, SvelteKit side) | `pnpm add @pointmatic/quizazz` |

### Versioning policy

- **Single project version**, loose semver `vX.Y.Z`. Canonical source: [`python/pyproject.toml`](../../python/pyproject.toml) `[project].version`, mirrored in `__version__`.
- **X** bumps on breaking changes or a big new thing (first public release, manifest-schema break). **Y** bumps on a feature (one story) or a bundle once stable. **Z** on bug fixes and trivial changes.
- Both published packages — `quizazz` on PyPI and `@pointmatic/quizazz` on npm — release at the same project version, in lockstep. If only one package has meaningful changes, the other re-releases at the new version anyway; the cost is trivial and the user-visible consistency is worth it.
- `MANIFEST_SCHEMA_VERSION` is a **separate protocol marker** embedded in every compiled manifest under the top-level `schemaVersion` field. Bumps only on actual manifest-shape changes — not every project-version bump.
