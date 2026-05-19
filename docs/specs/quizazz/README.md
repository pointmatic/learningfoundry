# Quizazz

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

A browser-based study tool that quizzes you on your understanding of a topic. Questions are authored in YAML and organized into quizzes with topics, subtopics, and a navigation tree. A Python builder validates and compiles the YAML into an optimized JSON manifest, and a SvelteKit app presents interactive multiple-choice quizzes. A weighted-random algorithm tracks your performance and prioritizes the material you struggle with most.

## Features

- **Multi-quiz support** — organize questions into quizzes with topics, subtopics, and a navigation tree
- **YAML question authoring** — write questions with categorized answers, explanations, and subtopic grouping
- **Python builder** — validates YAML schema and compiles to optimized JSON manifest (single or batch mode)
- **Navigation tree** — browse topics and subtopics, see mastery scores, and select what to study
- **Weighted selection** — questions you get wrong appear more frequently
- **Mastery tracking** — per-topic and per-subtopic mastery percentages based on cumulative scores
- **Keyboard-first** — navigate the entire quiz with keyboard shortcuts
- **Persistent scores** — client-side SQLite (sql.js/WASM) persisted to IndexedDB, isolated per quiz
- **Review mode** — after each quiz, review every answer with explanations; navigate between questions with carousel
- **Mid-quiz review** — go back to review previously answered questions without losing progress
- **Tag filtering** — optionally filter questions by topic tags before starting
- **Configurable** — choose question count (1–N) and answer choices (3, 4, or 5)

## Repository Structure

| Directory | Purpose |
|-----------|---------|
| `app/` | SvelteKit quiz UI; also publishes `@pointmatic/quizazz` npm package (Phase L) |
| `python/` | `quizazz` Python package (published to PyPI): validator, compiler, CLI, library API |
| `data/` | YAML question banks organized by quiz |
| `docs/` | Specifications, tech spec, and stories |

## Prerequisites

- **Node.js** 22+ and **pnpm** 10+
- **Python** 3.12+ with a virtual environment

## Setup

### 1. Python Builder

The builder is published to PyPI and can be installed into any Python 3.12+ environment:

```bash
pip install quizazz
```

For development against a local checkout:

> **Tip:** Consider installing the Homebrew package [Pyve](https://pointmatic.github.io/pyve) to automatically handle virtual environment setup and activation.

```bash
# From the repository root (with venv activated)
./install.sh
```

### 2. Compile Questions

**Single quiz** (compile one quiz directory):

```bash
quizazz generate --input data/aws-ml-specialty-exam/
```

**Batch mode** (compile all quizzes under a parent directory):

```bash
quizazz generate --all --input data/
```

Both `--input` and `--output` have sensible defaults (`data/quiz/` and `app/src/lib/data/`).

### 3. SvelteKit App

```bash
pnpm --dir app install
```

### 4. Run the Quiz

After compiling questions and installing dependencies:

```bash
quizazz run
```

This builds the app (if needed), starts a local server, and opens the quiz in your browser at `http://localhost:8000`. Use `--port` to change the port.

For development with hot reload:

```bash
pnpm --dir app dev
```

## Usage

### Authoring Questions

Each quiz lives in its own directory under `data/`. YAML files within a quiz directory become **topics** in the navigation tree. Each file can optionally contain `menu_name`, `menu_description`, and `subtopic` groupings.

**Simple format** (flat questions):

```yaml
menu_name: "General Knowledge"
menu_description: "A mix of geography, science, and more"

questions:
  - question: "What is the capital of France?"
    tags: ["geography"]
    answers:
      correct:
        - text: "Paris"
          explanation: "Paris has been the capital since the 10th century."
      partially_correct:
        - text: "Lyon"
          explanation: "Lyon is the second-largest city but not the capital."
      incorrect:
        - text: "Berlin"
          explanation: "Berlin is the capital of Germany."
      ridiculous:
        - text: "Atlantis"
          explanation: "Atlantis is a mythical city."
        - text: "The Moon"
          explanation: "The Moon is not a city."
```

**Subtopic format** (grouped questions):

```yaml
menu_name: "Advanced Concepts"
menu_description: "Challenging questions on algorithms and physics"

questions:
  - subtopic: "Algorithms"
    questions:
      - question: "What is the worst-case time complexity of quicksort?"
        tags: ["algorithms"]
        answers:
          correct:
            - text: "O(n²)"
              explanation: "Quicksort degrades to O(n²) with poor pivot selection."
          # ... more answer categories
  - subtopic: "Physics"
    questions:
      - question: "What is the Heisenberg Uncertainty Principle?"
        tags: ["physics"]
        answers:
          correct:
            - text: "Position and momentum cannot both be known exactly"
              explanation: "Δx·Δp ≥ ℏ/2"
          # ... more answer categories
```

**Requirements per question:**
- At least **5 answers** total
- At least **1** answer in each category: `correct`, `partially_correct`, `incorrect`, `ridiculous`
- **`tags`** is optional — a list of lowercase strings for filtering (e.g., `["math", "science"]`)
- **`menu_name`** and **`menu_description`** are optional — displayed in the navigation tree
- **`subtopic`** groups are optional — create subtopic nodes in the navigation tree

After editing YAML files, recompile:

```bash
quizazz generate --input data/aws-ml-specialty-exam/
```

### Creating a New Quiz

1. Create a new directory under `data/`, e.g., `data/my-quiz/`
2. Add YAML files with questions (each file becomes a topic)
3. Optionally use subdirectories for organization (they become directory nodes in the nav tree)
4. Compile: `quizazz generate --input data/my-quiz/`
5. Run the app: `quizazz run`

### Taking a Quiz

1. **Navigate** — browse the topic tree, see mastery scores, and select topics/subtopics to study
2. **Configure** — filter by tags (optional), choose question count and answer choices
3. **Answer** — select an answer and submit
4. **Review answered** (optional) — go back mid-quiz to review previously answered questions
5. **Review** — after the quiz, see your score and review every answer with explanations
6. **Retake** or **Start New** — retake the same questions or start fresh

Mastery badges show your progress: green (≥80%), amber (≥40%), gray (<40%). When tags are selected, only questions matching **any** selected tag are included (OR logic). The question count slider adjusts automatically to the filtered pool size.

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `a`–`e` | Select an answer |
| `Enter` | Submit selected answer |
| `Escape` | Go back (to answered questions, summary, or quiz) |
| `←` / `→` | Navigate between questions in review mode |

## Scoring

| Answer Category | Points |
|-----------------|--------|
| Correct | **+1** |
| Partially correct | **−2** |
| Incorrect | **−5** |
| Ridiculous | **−10** |

Scores accumulate per question across sessions. The selection algorithm uses the formula `weight = max_score − score + 1`, so lower-scored questions are drawn more frequently.

## CLI Reference

| Command | Description |
|---------|-------------|
| `quizazz generate` | Compile YAML question banks into a quiz manifest |
| `quizazz build` | Build the Svelte application for production |
| `quizazz build --standalone <name>` | Build a single-quiz SPA bundling only `<name>.json` (see "Standalone single-quiz SPA" below) |
| `quizazz run` | Launch a local web server and open the app |

All commands support `--help` for full option details.

## Standalone single-quiz SPA

When the SPA only needs to ship one quiz — for embedding on a course page,
training portal, or kiosk where the chooser screen is just clutter —
`quizazz build --standalone <name>` produces a one-quiz bundle from
the manifest already compiled at `app/src/lib/data/<name>.json`:

```bash
quizazz generate --input data/aws-ml-specialty-exam/
quizazz build --standalone aws-ml-specialty-exam
# → app/build/ contains a SPA that loads aws-ml-specialty-exam directly,
#   with the chooser and manifest-upload UI elided
```

What changes vs. the default build:

- The CLI temporarily moves every other `*.json` under `app/src/lib/data/`
  to a `TemporaryDirectory` for the duration of the `pnpm build`, so the
  Vite glob (`import.meta.glob('./*.json', { eager: true })`) only picks
  up the target. After the build, every moved manifest is restored — the
  source tree is left exactly as it started, even if the build crashes
  or is `Ctrl+C`'d mid-run.
- The CLI exports `QUIZAZZ_STANDALONE=<name>` and
  `VITE_QUIZAZZ_STANDALONE=<name>` to the build subprocess. The app
  reads the prefixed form (Vite only exposes `VITE_*` vars to
  `import.meta.env`) and skips straight to the navigation tree on first
  paint — no chooser, no manifest-upload UI.
- If `<name>.json` doesn't exist under `app/src/lib/data/`, the CLI exits
  with a clear error before invoking pnpm, and no manifests are moved.
  If the runtime check fails (the env var is set but the manifest didn't
  end up bundled), the SPA renders an explicit "build misconfiguration"
  message instead of a blank screen.
- The non-standalone path (`quizazz build` without `--standalone`) is
  unchanged and continues to bundle every manifest in `app/src/lib/data/`.

## Library API (UC-3)

Host frameworks can compile assessment YAML directly into a manifest dict at their own build time, without shelling out to the CLI or writing intermediate files. Three symbols are re-exported from the package root:

```python
from pathlib import Path
from quizazz import compile_assessment, validate_assessment, ValidationError

try:
    manifest = compile_assessment("module-4-pre.yaml", base_dir=Path("content"))
    # manifest → dict with schemaVersion, quizName, tree, questions
except ValidationError as exc:
    print(exc.file_path, exc.message, exc.detail)

errors = validate_assessment("bad.yaml", base_dir=Path("content"))
# errors → [] on success, or one human-readable string per violation
```

Both functions accept `str` or `Path` for their arguments. `yaml_path` is joined under `base_dir` and must resolve strictly inside it; traversal attempts (`..`, absolute paths outside the base, symlinks that escape) raise `ValidationError` with `detail={"base_dir": ..., "resolved": ...}`. Neither function writes to disk, spawns subprocesses, or issues network calls. Both are synchronous.

`validate_assessment` never raises — it swallows `ValidationError` and surfaces one error string per violation in the returned list.

## Embed in your own SvelteKit app

Phase L ships the browser half of the host-integration contract as the
`@pointmatic/quizazz` npm package. A host SvelteKit app imports a single
`<QuizBlock>` component and renders a full quiz inline from a manifest
produced by `compile_assessment` above.

```bash
pnpm add @pointmatic/quizazz
```

```svelte
<script lang="ts">
  import { QuizBlock } from '@pointmatic/quizazz';
  import '@pointmatic/quizazz/styles.css';
  import manifest from './module-4-pre-quiz.json';

  function handleComplete(e) {
    console.log(`Quiz ${e.quizRef}: scored ${e.score}/${e.maxScore}`);
  }
</script>

<QuizBlock {manifest} quizRef="module-4-pre" oncomplete={handleComplete} />
```

Two host-side setup steps are required:

1. Disable SSR on the route that mounts `<QuizBlock>` (sql.js + IndexedDB
   are browser-only). Add `export const ssr = false;` to the route's
   `+page.ts` or `+layout.ts`.
2. Import the precompiled styles bundle once:
   `import '@pointmatic/quizazz/styles.css';`. The bundle ships only the
   utilities the component uses (no Tailwind preflight, no project-wide
   footprint) so it composes cleanly whether or not your host already
   uses Tailwind.

No WASM copy step is needed: `<QuizBlock>` imports the `sql-wasm.wasm`
asset via Vite's `?url` pattern, so the host's build emits it
automatically into the build output.

The full embedding reference — theming custom properties, the `complete`
event's DOM-event form, the single-instance-per-page guard, and the
SvelteKit host setup steps — lives alongside the source at
[`app/src/lib/embed/README.md`](app/src/lib/embed/README.md).

## Testing

```bash
# App tests
pnpm --dir app vitest run

# Builder tests
python -m pytest python/
```

## Building for Production

```bash
quizazz build
```

The static site is output to `app/build/`.

## License

Apache-2.0 — see [LICENSE](LICENSE) for details.
