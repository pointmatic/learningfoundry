# tech_spec.md — Quizazz (SvelteKit + Node + Python)

## Overview

This document defines **how** Quizazz is built — architecture, module layout, dependencies, data models, and cross-cutting concerns. For requirements and behavior, see [`features.md`](features.md). For the phased implementation plan, see [`stories.md`](stories.md). For the multi-quiz design rationale, see [`multi_quiz_features.md`](multi_quiz_features.md).

---

## Runtime & Tooling

| Concern | Choice | Notes |
|---------|--------|-------|
| **App framework** | SvelteKit 2.x | Static SPA via `@sveltejs/adapter-static` |
| **Language** | TypeScript 5.x | Strict mode enabled |
| **Styling** | Tailwind CSS 4.x | Utility-first; minimal custom CSS |
| **Component library** | None (hand-rolled) | Keep dependencies minimal; Lucide icons for iconography |
| **Client-side DB** | sql.js (WASM) | SQLite compiled to WASM, persisted to IndexedDB |
| **Build tool** | Vite (via SvelteKit) | Standard SvelteKit toolchain |
| **Python runtime** | Python 3.12+ | Used only in `builder/` for YAML validation/compilation |
| **Python package manager** | pip | Within venv managed by pyve/direnv |
| **Node package manager** | pnpm | Workspace-aware, fast |
| **Linter (JS/TS)** | ESLint + Prettier | SvelteKit defaults |
| **Linter (Python)** | Ruff | Fast, replaces flake8/isort/black |
| **Test runner (JS/TS)** | Vitest | Vite-native, fast |
| **Test runner (Python)** | pytest | Standard |

---

## Dependencies

### App Runtime Dependencies (`app/package.json`)

| Package | Purpose |
|---------|---------|
| `svelte` | UI framework |
| `@sveltejs/kit` | App framework |
| `@sveltejs/adapter-static` | Static site generation |
| `sql.js` | SQLite WASM for client-side database |
| `lucide-svelte` | Icon library |

### App Dev Dependencies (`app/package.json`)

| Package | Purpose |
|---------|---------|
| `typescript` | Type checking |
| `tailwindcss` | Utility CSS framework |
| `@tailwindcss/vite` | Tailwind Vite plugin |
| `vitest` | Unit/integration testing |
| `@testing-library/svelte` | Component testing utilities |
| `eslint` | Linting |
| `prettier` | Code formatting |
| `prettier-plugin-svelte` | Svelte formatting support |

### Builder Dependencies (`builder/pyproject.toml`)

| Package | Purpose |
|---------|---------|
| `pyyaml` | YAML parsing |
| `pydantic` | Data validation and schema enforcement |
| `pytest` | Testing |
| `ruff` | Linting and formatting |

---

## Repository Structure

```
quizazz/
├── LICENSE                          # Apache-2.0
├── README.md                        # Project overview, setup, usage
├── data/
│   ├── quiz/                        # Default quiz (ships with repo)
│   │   └── sample.yaml
│   └── <other-quiz>/                # User-created quizzes (sibling dirs)
│       ├── topic-a.yaml
│       └── subtopics/
│           └── topic-b.yaml
├── app/
│   ├── package.json
│   ├── svelte.config.js
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── static/
│   │   └── sql-wasm.wasm            # sql.js WASM binary (copied at build)
│   ├── src/
│   │   ├── app.html                 # SvelteKit shell
│   │   ├── app.css                  # Tailwind imports + global styles
│   │   ├── lib/
│   │   │   ├── data/
│   │   │   │   ├── manifest.json    # Compiled quiz manifest (navigation tree + questions)
│   │   │   │   └── index.ts         # Typed exports: questions, allTags, navTree
│   │   │   ├── db/
│   │   │   │   ├── index.ts         # Barrel export for db module
│   │   │   │   ├── database.ts      # sql.js init, IndexedDB persistence, schema
│   │   │   │   └── scores.ts        # Score CRUD operations
│   │   │   ├── engine/
│   │   │   │   ├── lifecycle.ts     # Quiz lifecycle functions (start, submit, retake, etc.)
│   │   │   │   ├── selection.ts     # Weighted random question selection
│   │   │   │   ├── presentation.ts  # Answer selection and shuffling
│   │   │   │   ├── scoring.ts       # Point calculation per answer category
│   │   │   │   └── mastery.ts       # Per-topic/subtopic score aggregation
│   │   │   ├── stores/
│   │   │   │   └── quiz.ts          # Svelte stores for quiz state
│   │   │   ├── types/
│   │   │   │   └── index.ts         # TypeScript type definitions
│   │   │   ├── utils/
│   │   │   │   └── random.ts        # Shuffle and weighted random helpers
│   │   │   └── components/
│   │   │       ├── NavigationTree.svelte  # Topic/subtopic tree with mastery scores
│   │   │       ├── ConfigView.svelte
│   │   │       ├── QuizView.svelte
│   │   │       ├── SummaryView.svelte
│   │   │       ├── ReviewView.svelte
│   │   │       ├── AnsweredQuestionsView.svelte
│   │   │       └── ProgressBar.svelte
│   │   └── routes/
│   │       └── +page.svelte         # Single-page app (all views in one route)
│   └── tests/
│       ├── db/
│       │   └── scores.test.ts
│       ├── engine/
│       │   ├── selection.test.ts
│       │   ├── presentation.test.ts
│       │   ├── scoring.test.ts
│       │   └── mastery.test.ts
│       ├── integration/
│       │   ├── lifecycle.test.ts
│       │   ├── edge-cases.test.ts
│       │   ├── tags.test.ts
│       │   └── navigation.test.ts
│       └── utils/
│           └── random.test.ts
├── builder/
│   ├── pyproject.toml
│   ├── src/
│   │   └── quizazz_builder/
│   │       ├── __init__.py
│   │       ├── __main__.py          # CLI entry point: python -m quizazz_builder
│   │       ├── models.py            # Pydantic models for question/answer/quiz file schema
│   │       ├── validator.py         # YAML validation logic
│   │       ├── compiler.py          # YAML → JSON manifest compilation
│   │       └── manifest.py          # Navigation tree generation from directory structure
│   └── tests/
│       ├── test_models.py
│       ├── test_validator.py
│       ├── test_compiler.py
│       └── test_manifest.py
└── docs/
    ├── guides/
    │   └── project_guide.md
    └── specs/
        ├── features.md
        ├── tech_spec.md
        ├── stories.md
        └── multi_quiz_features.md
```

---

## Key Component Design

### Builder: `quizazz_builder.models`

Pydantic models that define and validate the YAML schema.

```python
class Answer(BaseModel):
    text: str                    # Non-empty answer text
    explanation: str             # Non-empty explanation

class AnswerSet(BaseModel):
    correct: list[Answer]        # >= 1
    partially_correct: list[Answer]  # >= 1
    incorrect: list[Answer]      # >= 1
    ridiculous: list[Answer]     # >= 1

    @model_validator(mode="after")
    def check_minimum_total(self) -> "AnswerSet":
        """Total answers across all categories must be >= 5."""

class Question(BaseModel):
    question: str                # Non-empty question text
    tags: list[str] | None = None  # Optional list of tags (normalized to lowercase)
    answers: AnswerSet

    @field_validator("tags", mode="before")
    def normalize_tags(cls, v):
        """Normalize tags to lowercase, reject empty strings."""

class SubtopicGroup(BaseModel):
    subtopic: str                # Non-empty subtopic name
    questions: list[Question]    # >= 1 question

class QuizFile(BaseModel):
    menu_name: str               # Non-empty display name for navigation tree
    menu_description: str = ""   # Optional short blurb for navigation tree
    quiz_description: str = ""   # Optional longer description shown on selection
    questions: list[Question | SubtopicGroup]  # Mix of bare questions and subtopic groups

    @model_validator(mode="after")
    def check_has_questions(self) -> "QuizFile":
        """File must contain at least one question (directly or via subtopics)."""
```

> **Migration note**: The previous `QuestionBank(RootModel[list[Question]])` is replaced by `QuizFile`. Existing YAML files (bare lists) must be migrated to the new format with `menu_name` and a `questions` key.

### Builder: `quizazz_builder.validator`

```python
def validate_file(path: Path) -> QuizFile:
    """Parse and validate a single YAML file against the QuizFile model.
    Raises QuizValidationError with file path, question index, and
    specific violation details."""

def validate_quiz_directory(quiz_dir: Path) -> list[tuple[Path, QuizFile]]:
    """Validate all .yaml files in a quiz directory (recursively).
    Returns a list of (relative_path, QuizFile) tuples preserving the
    directory hierarchy. Raises on first error."""
```

### Builder: `quizazz_builder.compiler`

```python
def compile_quiz(validated_files: list[tuple[Path, QuizFile]], output_dir: Path) -> None:
    """Compile a quiz directory into a manifest.json in output_dir.
    The manifest includes the navigation tree and all compiled questions.
    Each question gets a stable unique ID (SHA-256 hash of question text)."""
```

### Builder: `quizazz_builder.manifest`

```python
def build_navigation_tree(
    validated_files: list[tuple[Path, QuizFile]]
) -> dict:
    """Build a navigation tree from the directory structure and file metadata.
    Returns a nested dict representing directories, topics, and subtopics
    with question IDs at each leaf for score aggregation."""
```

### Builder: `quizazz_builder.__main__`

```python
# Single quiz:
#   python -m quizazz_builder --input data/quiz/ --output app/build/quiz/
#
# All quizzes:
#   python -m quizazz_builder --all --input data/ --output app/build/
#
# Exit 0 on success, exit 1 with descriptive error on validation failure.
# In --all mode, each immediate subdirectory of --input is treated as a
# separate quiz and compiled to its own subdirectory under --output.
```

### App: `lib/types/index.ts`

```typescript
export type AnswerCategory = "correct" | "partially_correct" | "incorrect" | "ridiculous";

export interface Answer {
  text: string;
  explanation: string;
  category: AnswerCategory;
}

export interface Question {
  id: string;           // Stable hash from builder
  question: string;
  tags: string[];       // Normalized lowercase tags (empty array if none)
  answers: Answer[];    // Flat list with category attached (from compiled JSON)
  topicId: string;      // ID of the topic (YAML file) this question belongs to
  subtopic: string | null;  // Subtopic name, or null if top-level
}

export interface NavNode {
  id: string;           // Unique node ID (derived from path)
  label: string;        // Display name (dir name or menu_name)
  description: string;  // menu_description (empty for directories)
  type: "directory" | "topic" | "subtopic";
  questionIds: string[];  // All question IDs within this node's scope
  children: NavNode[];  // Child nodes
}

export interface QuizManifest {
  quizName: string;     // Quiz directory name
  tree: NavNode[];      // Top-level navigation tree
  questions: Question[];  // All questions in the quiz
}

export interface QuizConfig {
  questionCount: number;
  answerCount: 3 | 4 | 5;
  selectedTags: string[];  // Empty array = no filter (all questions)
  selectedNodeIds: string[];  // Navigation tree node IDs scoping the question pool
}

export interface PresentedAnswer extends Answer {
  label: string;        // "a", "b", "c", "d", "e"
}

export interface QuizQuestion {
  question: Question;
  presentedAnswers: PresentedAnswer[];
  selectedLabel: string | null;
  submittedLabel: string | null;
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
```

### App: `lib/db/database.ts`

```typescript
import initSqlJs, { type Database } from "sql.js";

const DB_STORE = "database";
const DB_KEY = "db";

export function getDbName(quizName: string): string {
  /** Returns "quizazz-{quizName}" — each quiz gets its own IndexedDB. */
  return `quizazz-${quizName}`;
}

export async function initDatabase(quizName: string): Promise<Database> {
  /** Load sql.js WASM, restore DB from IndexedDB (keyed by quizName)
   *  if available, otherwise create fresh schema. */
}

export async function persistDatabase(db: Database, quizName: string): Promise<void> {
  /** Export DB to Uint8Array and save to IndexedDB for this quiz. */
}

export function createSchema(db: Database): void {
  /** Schema is unchanged — same tables, no quiz_path column needed
   *  because each quiz has its own database.
   *
   *  CREATE TABLE IF NOT EXISTS question_scores (
   *    question_id TEXT PRIMARY KEY,
   *    cumulative_score INTEGER DEFAULT 0
   *  );
   *  CREATE TABLE IF NOT EXISTS session_answers (
   *    id INTEGER PRIMARY KEY AUTOINCREMENT,
   *    session_id TEXT,
   *    question_id TEXT,
   *    selected_category TEXT,
   *    points INTEGER,
   *    timestamp INTEGER
   *  ); */
}
```

### App: `lib/db/scores.ts`

```typescript
export function getScores(db: Database): QuestionScore[] {
  /** SELECT question_id, cumulative_score FROM question_scores */
}

export function updateScore(db: Database, questionId: string, points: number): void {
  /** UPDATE question_scores SET cumulative_score = cumulative_score + ? WHERE question_id = ? */
}

export function seedScores(db: Database, questionIds: string[]): void {
  /** INSERT OR IGNORE for each question ID with score 0. */
}

export function recordAnswer(
  db: Database, sessionId: string, questionId: string,
  category: AnswerCategory, points: number
): void {
  /** INSERT into session_answers. */
}
```

### App: `lib/engine/selection.ts`

```typescript
export function selectQuestions(
  questions: Question[],
  scores: QuestionScore[],
  count: number
): Question[] {
  /**
   * Weighted random selection without replacement.
   *
   * Weight formula: weight = max_score - score + 1
   *   where max_score = max(all cumulative scores)
   *   This ensures all weights are positive (minimum weight = 1).
   *
   * Algorithm:
   * 1. Compute weight for each question.
   * 2. Pick a random question proportional to weight.
   * 3. Remove it from the pool.
   * 4. Repeat until count is reached or pool is exhausted.
   */
}
```

### App: `lib/engine/presentation.ts`

```typescript
export function presentAnswers(
  question: Question,
  answerCount: 3 | 4 | 5
): PresentedAnswer[] {
  /**
   * 1. Pick one random answer from the "correct" category.
   * 2. Collect all non-correct answers into a pool.
   * 3. Randomly pick (answerCount - 1) from the pool.
   * 4. Combine, shuffle, and assign labels "a" through "e".
   */
}
```

### App: `lib/engine/scoring.ts`

```typescript
export const SCORE_MAP: Record<AnswerCategory, number> = {
  correct: 1,
  partially_correct: -2,
  incorrect: -5,
  ridiculous: -10,
};

export function scoreAnswer(category: AnswerCategory): number {
  return SCORE_MAP[category];
}
```

### App: `lib/engine/mastery.ts`

```typescript
export interface MasteryScore {
  total: number;        // Total questions in scope
  positive: number;     // Questions with cumulative_score > 0
  percent: number;      // Math.round((positive / total) * 100)
}

export function computeMastery(
  questionIds: string[],
  scores: QuestionScore[]
): MasteryScore {
  /** Compute mastery percentage for a set of question IDs.
   *  Used by NavigationTree to display per-node scores. */
}
```

### App: `lib/stores/quiz.ts`

```typescript
import { writable, derived } from "svelte/store";

/** Reactive stores for the quiz lifecycle. */

export const quizSession = writable<QuizSession | null>(null);
export const viewMode = writable<
  "nav" | "config" | "quiz" | "quiz-answered" | "quiz-review" | "summary" | "review"
>("nav");
export const reviewIndex = writable<number | null>(null);

export const currentQuestion = derived(quizSession, ($session) => {
  if (!$session) return null;
  return $session.questions[$session.currentIndex];
});

export const progress = derived(quizSession, ($session) => {
  if (!$session) return { current: 0, total: 0, percent: 0 };
  const answered = $session.questions.filter((q) => q.submittedLabel !== null).length;
  return {
    current: answered,
    total: $session.questions.length,
    percent: Math.round((answered / $session.questions.length) * 100),
  };
});
```

### App: `routes/+page.svelte`

Single-page app with seven view states managed by the `viewMode` store:

| View | Component | Description |
|------|-----------|-------------|
| `nav` | `NavigationTree` | Topic/subtopic tree with mastery scores; select nodes to scope quiz |
| `config` | `ConfigView` | Tag filter toggles, question count slider, answer count buttons, Start button |
| `quiz` | `QuizView` | Question display, answer selection, progress bar, Submit |
| `quiz-answered` | `AnsweredQuestionsView` | Mid-quiz list of previously answered questions |
| `quiz-review` | `ReviewView` | Mid-quiz review of a single answered question |
| `summary` | `SummaryView` | Score %, question list with ✓/✗, Retake/Start/Quit buttons |
| `review` | `ReviewView` | Post-quiz question detail with explanations, ← Back button, ←/→ carousel |

All views are rendered inline in `+page.svelte` using conditional blocks (`{#if}`). No SvelteKit routing is used beyond the single page — all navigation is state-driven.

---

## Data Models

### Compiled JSON Manifest (output of builder)

Each quiz directory compiles to a single `manifest.json`:

```json
{
  "quizName": "quiz",
  "tree": [
    {
      "id": "sample",
      "label": "European Capitals",
      "description": "Capital cities of European countries",
      "type": "topic",
      "questionIds": ["a1b2c3d4...", "e5f6g7h8..."],
      "children": [
        {
          "id": "sample/western-europe",
          "label": "Western Europe",
          "description": "",
          "type": "subtopic",
          "questionIds": ["a1b2c3d4..."],
          "children": []
        }
      ]
    }
  ],
  "questions": [
    {
      "id": "a1b2c3d4...",
      "question": "What is the capital of France?",
      "tags": ["geography", "europe"],
      "topicId": "sample",
      "subtopic": "Western Europe",
      "answers": [
        { "text": "Paris", "explanation": "Paris has been...", "category": "correct" },
        { "text": "Lyon", "explanation": "Lyon is the...", "category": "partially_correct" },
        { "text": "Berlin", "explanation": "Berlin is...", "category": "incorrect" },
        { "text": "Atlantis", "explanation": "Atlantis is...", "category": "ridiculous" },
        { "text": "The Moon", "explanation": "The Moon is...", "category": "ridiculous" }
      ]
    }
  ]
}
```

The builder flattens the categorized YAML structure into a flat answer list with an explicit `category` field. Questions carry `topicId` and `subtopic` references for navigation tree score aggregation.

### SQLite Schema

```sql
CREATE TABLE IF NOT EXISTS question_scores (
  question_id   TEXT PRIMARY KEY,
  cumulative_score INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS session_answers (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id      TEXT NOT NULL,
  question_id     TEXT NOT NULL,
  selected_category TEXT NOT NULL,
  points          INTEGER NOT NULL,
  timestamp       INTEGER NOT NULL
);
```

`session_answers` stores individual answer records for potential future analytics. It is written to but only read during the current session (for the review screen). The `session_id` is a UUID generated when a quiz starts.

The schema is identical across all quizzes — isolation is achieved at the IndexedDB level (one database per quiz, named `quizazz-{quizName}`).

---

## Cross-Cutting Concerns

### Database Persistence Strategy

1. On app load: determine quiz name from the manifest; attempt to restore DB from IndexedDB (`quizazz-{quizName}`).
2. If missing or corrupt: create fresh DB, create schema, seed scores from the manifest's question list.
3. After each score update: persist DB to IndexedDB (debounced if needed, but given the low frequency of writes — one per question — immediate persistence is fine).
4. On retake/new quiz: no DB reset; scores accumulate across all sessions.
5. Each quiz has its own IndexedDB database — no cross-quiz interference.

### Error Handling

| Layer | Strategy |
|-------|----------|
| Builder (Python) | Raise `SystemExit` with descriptive message on validation failure. Pydantic `ValidationError` provides field-level detail. |
| App build | If `manifest.json` is missing or empty, Vite build fails (import error). |
| App runtime (DB) | Wrap sql.js operations in try/catch. On unrecoverable error, show a user-friendly error banner with a "Reset Database" option. |
| App runtime (UI) | Svelte error boundaries where applicable. Defensive checks on store state. |

### Keyboard Interaction Map

| Key | Context | Action |
|-----|---------|--------|
| `a`–`e` | Quiz view | Select corresponding answer |
| `Enter` | Quiz view (answer selected) | Submit answer |
| `Enter` | Config view (valid config) | Start quiz |
| `Escape` | Quiz view (has answered) | Show answered questions list |
| `Escape` | Quiz-answered / quiz-review | Return to current question |
| `Escape` | Review view | Return to summary |
| `←` / `→` | Review view / quiz-review | Navigate between reviewed questions |

### WASM Binary Handling

The `sql-wasm.wasm` file must be available at runtime. Strategy:
1. Copy `node_modules/sql.js/dist/sql-wasm.wasm` to `app/static/` during setup (npm postinstall script or manual).
2. Initialize sql.js with `locateFile: (file) => \`/${file}\`` so it loads from the static directory.

---

## Testing Strategy

### Python (builder)

| Test file | Covers |
|-----------|--------|
| `test_models.py` | Pydantic model validation: valid questions, missing fields, empty strings, insufficient answers, category constraints, QuizFile metadata, SubtopicGroup validation |
| `test_validator.py` | File-level validation: valid YAML, malformed YAML, missing files, empty files, QuizFile format, subtopic groups, recursive directory validation |
| `test_compiler.py` | Manifest output: correct structure, stable IDs (hash consistency), category flattening, topicId/subtopic references |
| `test_manifest.py` | Navigation tree: directory hierarchy, topic/subtopic nesting, questionIds at each node |

### TypeScript (app)

| Test file | Covers |
|-----------|--------|
| `scores.test.ts` | Score CRUD: seed, update, get; cumulative behavior; missing question handling |
| `selection.test.ts` | Weighted selection: all questions selectable, lower scores favored (statistical test over N iterations), pool exhaustion, topic/subtopic scoping |
| `presentation.test.ts` | Answer presentation: exactly 1 correct, correct total count, all labels assigned, shuffling |
| `scoring.test.ts` | Point values per category |
| `mastery.test.ts` | Per-topic/subtopic mastery computation from question-level scores |
| `random.test.ts` | Shuffle uniformity, weighted random correctness |
| `lifecycle.test.ts` | Integration: full quiz flows (nav→config→quiz→summary→review), derived stores, submit edge cases, DB integration, mid-quiz review |
| `edge-cases.test.ts` | Edge cases: 1 question, max questions, answer counts 3/4/5, min/many answers, uniform scores, negative scores |
| `navigation.test.ts` | Navigation tree rendering, topic/subtopic selection, score aggregation display |
