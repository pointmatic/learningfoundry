# features.md — Quizazz (SvelteKit + Node + Python)

## Overview

This document defines **what** the `quizazz` project does -- requirements, inputs, outputs, behavior -- without specifying **how** it is implemented. This is the source of truth for scope.

For a high-level concept (why), see [`concept.md`](concept.md). For implementation details (how), see [`tech-spec.md`](tech-spec.md). For a breakdown of the implementation plan (step-by-step tasks), see [`stories.md`](stories.md). For project-specific must-know facts that future LLMs need to avoid blunders, see [`project-essentials.md`](project-essentials.md). For the workflow steps tailored to the current mode (cycle steps, approval gates, conventions), see [`docs/project-guide/go.md`](../project-guide/go.md) — re-read it whenever the mode changes or after context compaction.


---

## Project Goal

Quizazz is a fully-owned, offline-capable quiz engine that delivers multiple-choice assessments from version-controlled YAML source. A Python builder validates the YAML and compiles a navigation/question manifest. A SvelteKit app — or, when embedded, a single SvelteKit component — presents the quiz, tracks per-question mastery in a client-side SQLite database (via sql.js/WASM, persisted to IndexedDB), and prioritizes weaker questions through weighted-random selection.

Quizazz is designed to serve four distinct use cases from the same core engine, without forking codebases:

| # | Use Case | Audience | Shape |
|---|----------|----------|-------|
| UC-1 | **Standalone single-quiz SPA** | Self-directed learners, authors shipping a one-off quiz | One quiz → one independent static SPA, deployable anywhere |
| UC-2 | **Multi-quiz hub SPA** | Authors managing several quiz banks in one place | Single SPA with a quiz chooser and runtime upload of externally-compiled quizzes |
| UC-3 | **Embeddable assessment component** | Host curriculum / learning frameworks (e.g., [`learningfoundry`](learningfoundry/consumer-dependency-spec.md), which in turn powers curricula) | Quizazz ships a **Python library** for build-time YAML compilation and a **SvelteKit `<QuizBlock>` component** for in-page runtime delivery; the host invokes the library during its own build and embeds the component in its own pages |
| UC-4 | **LLM-assisted question generation pipeline** *(future)* | Authors generating questions at scale from source material | `python/` toolchain that drives LLMs to produce validated YAML |

UC-1, UC-2, and UC-3 are in scope for v1. UC-4 is deferred; the `python/` workspace exists today partly to hold this future pipeline.

The repository is organized as a monorepo:

| Directory | Purpose |
|-----------|---------|
| `app/` | SvelteKit quiz UI, runtime engine, embeddable `<QuizBlock>` component, and build tooling (TypeScript, Tailwind CSS) |
| `python/` | Python YAML validation, manifest compilation, and public library API (Pydantic) |
| `data/` | Quiz source directories — each subdirectory is an independent quiz package |
| `docs/` | Concept, features, tech spec, stories, integration spec, and project-guide |

---

## Core Requirements

1. **Multi-quiz authoring** — Each subdirectory under `data/` is an independent quiz. The builder compiles one quiz or all quizzes in batch. Each quiz is fully isolated (own manifest, own database, own identity).
2. **YAML question bank** — Questions and answers are defined in YAML files with per-file metadata (`menu_name`, `menu_description`, `quiz_description`). Questions can be grouped under optional subtopics.
3. **Four-category answer classification** — Each answer belongs to one of `correct`, `partially_correct`, `incorrect`, or `ridiculous`, each with a distinct point value.
4. **Navigation tree** — The SPA presents a navigation tree mirroring the quiz's directory/file/subtopic hierarchy; the user selects scope from the tree before configuring a quiz.
5. **Mastery display** — Each tree node shows an aggregated mastery percentage computed from the per-question scores of questions within that node's scope.
6. **Weighted random selection** — Questions are drawn without replacement using weights derived from cumulative score, so weaker questions appear more often while every question retains a nonzero probability.
7. **Interactive quiz UI** — A minimalist, modern web interface presents one multiple-choice question at a time with 3, 4, or 5 answer choices.
8. **Deferred scoring with answer changing** — The user can change their selection on the current question until submission; scoring is committed on submit, not on first click.
9. **Per-quiz score persistence** — Cumulative per-question scores persist across sessions in a client-side SQLite database, isolated per quiz.
10. **Results summary with drill-down** — After completion, the user sees overall score, per-question outcome, and can drill into any question to review all presented answers, explanations, and categories.
11. **Tag filtering** — Questions may include optional tags; the config screen lets the user filter the pool by one or more tags (OR logic).
12. **Per-question timer** — Each question displays elapsed time on that question, informational only in v1.
13. **Standalone SPA packaging (UC-1)** — The same app can be built as a single-quiz standalone SPA, with the chooser/upload UI hidden or elided, opening directly into one specific quiz.
14. **Multi-quiz hub (UC-2)** — The default build presents a quiz chooser listing all pre-bundled quizzes, plus an interface to upload an externally-compiled quiz manifest at runtime.
15. **Embeddable host integration (UC-3)** — Quizazz exposes two integration surfaces for host frameworks: a **Python library API** for build-time assessment compilation and validation, and an **embeddable SvelteKit `<QuizBlock>` component** that renders a compiled manifest inline in the host's own pages and emits an aggregate completion event. Quizazz does not prescribe gating logic, host progress persistence, or host UI.

## Operational Requirements

16. **Build-time validation** — The builder validates every YAML file against the schema rules and fails fast with messages identifying the offending file, question, and specific violation. No partially valid manifest is ever emitted.
17. **Graceful runtime error handling** — Corrupt databases, missing manifests, and invalid uploaded packages display a user-friendly message rather than a blank screen or stack trace, and offer a recovery path where possible (reset DB, re-upload, return to chooser).
18. **Database initialization** — On first load (or if the database is missing/corrupt), the app creates the schema, seeds per-question scores to zero, and persists to IndexedDB. Subsequent loads restore from IndexedDB.
19. **Zero network at runtime** — After initial page load, the SPA (or embedded component) makes no network requests. The sql.js WASM binary is bundled with the app.
20. **Unified CLI** — A single `quizazz` command covers the full authoring/build/run workflow for UC-1 and UC-2: `quizazz generate` (YAML → manifest), `quizazz build` (SvelteKit production build), `quizazz run` (local server + browser launch). Each subcommand supports `--help` and has sensible defaults.
21. **Package distribution** — The Python builder is distributed as `quizazz` on PyPI (importable library + `quizazz` CLI). The embeddable SvelteKit component is distributed as `@pointmatic/quizazz` on npm (or bundled into the host's SvelteKit template). Semantic versioning applies; the **compiled manifest schema is the versioning boundary** between the Python library and the SvelteKit component — breaking changes to the manifest structure require a major version bump in both.

## Quality Requirements

22. **Reliable comprehension signal** — Cumulative scores and mastery aggregates must meaningfully reflect the learner's actual understanding, so an external system (or the learner) can trust them for skip/retry decisions.
23. **Fair question selection** — The weighted random algorithm guarantees that every question in the filtered pool has a nonzero probability of being drawn, regardless of score.
24. **Non-seeded shuffling** — Answer order is randomized independently per question presentation (not seeded), so repeat presentations feel fresh.
25. **Minimal dependencies** — Runtime dependencies are limited to what the SPA strictly needs; no CDN loads, no telemetry, no analytics.
26. **Cross-platform authoring** — The builder runs on Linux, macOS, and Windows (Python 3.12+); the SPA runs in any modern evergreen browser.
27. **Host-friendly embedding (UC-3)** — The `<QuizBlock>` component must be self-contained (no external network or server dependency, polished default rendering without requiring the host to bring its own CSS framework), must not leak keyboard events the host expects to handle globally, and must expose CSS custom properties as the universal theming surface — with host Tailwind utilities layering additively when present.

## Usability Requirements

28. **Keyboard-first interaction** — Answers selectable via `a`–`e`, submission via `Enter`, back-navigation via `Escape`, review carousel via `←`/`→`. All keyboard actions have mouse/touch equivalents. These behaviors apply equally to standalone, hub, and embedded modes.
29. **Progress indication** — A progress bar and "Question N of M" label are visible throughout the quiz.
30. **Quiz configuration flow (UC-1 / UC-2)** — The user (a) selects topics/subtopics from the navigation tree, (b) optionally filters by tags, (c) chooses question count (1–pool size) and answer count (3/4/5), then (d) starts the quiz. In UC-3 (embedded), the manifest itself *is* the question set — the nav/config screens are not presented.
31. **Mid-quiz review** — During a quiz, the user can press `Escape` to review answered questions (with full explanations) and return to the current unanswered question without losing progress.
32. **Post-quiz actions** — From the results summary the user can **Retake** (same questions, reshuffled answers), **Start** (return to navigation/configuration for a fresh quiz), or **Quit** (return to navigation). In UC-3, post-quiz actions are governed by the host layout; Retake may be offered by the component, while "Start"/"Quit" are not meaningful.
33. **Responsive layout** — The UI adapts to common desktop and tablet viewport sizes. Mobile native wrappers are out of scope; responsive web layout is not.

---

## Non-Goals

- **User accounts / authentication** — Quizazz is single-user and local-first.
- **Server-side persistence** — All data lives in the browser (IndexedDB-backed SQLite).
- **Real-time multiplayer** — No collaborative or competitive features.
- **In-browser question editing** — Questions are authored in YAML and compiled; there is no WYSIWYG editor.
- **Native mobile wrappers** — Browser-only.
- **Non-MCQ question formats** — Fill-in-the-blank, short free-response, and LLM-as-judge "teach me" exercises are out of scope. In the consumer / learningfoundry context, these formats live in Jupyter notebooks alongside the Quizazz-delivered MCQ assessments.
- **Host-supplied scope overrides for embedded quizzes** — In UC-3 v1, the manifest *is* the full assessment; the host cannot pass topic/subtopic scope, question count, or tag filter to narrow it further at runtime. See Future Vision.
- **Per-question outcome streaming to host** — In UC-3 v1, the host receives only an aggregate `{quizRef, score, maxScore, questionCount}` payload on completion. Per-question outcomes remain inside Quizazz's IndexedDB. See Future Vision.
- **Host progress persistence** — Quizazz does not write to any host database; the host is responsible for persisting the completion event payload.
- **Score decay / spaced repetition** — Deferred; see Future Vision.
- **Session history / longitudinal analytics** — Deferred; see Future Vision.
- **LLM-powered question generation (UC-4)** — Architecturally planned; not in v1.
- **Answer-length normalization** — Deferred; see Future Vision.
- **Post-quiz quality rating / complaint signals** — Deferred; see Future Vision.
- **Persisted runtime uploads** — Uploaded quizzes are session-only in v1; persistence across reloads is deferred.
- **Server-side API (`api/` workspace)** — A future FastAPI backend is architecturally anticipated but not in v1.

---

## Inputs

### Quiz Directory Layout

Each quiz is a directory under `data/`. The directory may contain any number of `.yaml` files organized into any hierarchy of subdirectories:

```
data/
  quiz/                          ← default quiz (ships with repo)
    sample.yaml
    advanced/
      topic-a.yaml
      topic-b.yaml
  aws-ml-specialty-exam/         ← additional pre-bundled quiz
    domain1-data-engineering.yaml
    domain2-exploratory-data-analysis.yaml
    ...
  my-custom-quiz/                ← user-created quiz
    fundamentals.yaml
    pipelines/
      batch.yaml
      streaming.yaml
```

All quiz directories are treated equally by the builder; `data/quiz/` is only "special" in that it ships with the repo as an example.

### YAML Question File

Each `.yaml` file represents a **topic** and contains file-level metadata plus a list of questions (optionally grouped by subtopic):

```yaml
menu_name: "European Capitals"
menu_description: "Capital cities of European countries"
quiz_description: "Test your knowledge of European geography"
questions:
  - subtopic: "Western Europe"
    questions:
      - question: "What is the capital of France?"
        tags: ["geography", "europe"]
        answers:
          correct:
            - text: "Paris"
              explanation: "Paris has been the capital of France since the 10th century."
          partially_correct:
            - text: "Lyon"
              explanation: "Lyon is the second-largest city in France but is not the capital."
          incorrect:
            - text: "Berlin"
              explanation: "Berlin is the capital of Germany, not France."
          ridiculous:
            - text: "Atlantis"
              explanation: "Atlantis is a mythical city."
            - text: "The Moon"
              explanation: "The Moon is not a city."
  - question: "What is the capital of Switzerland?"
    answers:
      correct:
        - text: "Bern"
          explanation: "Bern is the federal capital of Switzerland."
      partially_correct:
        - text: "Zurich"
          explanation: "Zurich is the largest city but not the capital."
      incorrect:
        - text: "Vienna"
          explanation: "Vienna is the capital of Austria."
      ridiculous:
        - text: "Cheese Town"
          explanation: "Cheese Town is not a real place."
        - text: "Narnia"
          explanation: "Narnia is a fictional land."
```

**File-level metadata:**

| Field | Required | Description |
|-------|----------|-------------|
| `menu_name` | Yes | Display name shown in the navigation tree |
| `menu_description` | No | Short blurb shown alongside the menu entry |
| `quiz_description` | No | Longer description shown when the user selects this topic |
| `questions` | Yes | List of questions and/or subtopic groups |

**Question hierarchy:** The `questions` list can mix bare `Question` objects and `SubtopicGroup` objects (with `subtopic: str` and `questions: list[Question]`).

**Validation rules (enforced at build time by both the CLI and the Python library API, and again on runtime upload):**

| Rule | Description |
|------|-------------|
| Non-empty `menu_name` | Each file must have a non-empty `menu_name`. |
| Non-empty question text | The `question` field must be a non-empty string. |
| Minimum 5 answers per question | Total answer count across all categories must be ≥ 5. |
| At least 1 in every category | Each of `correct`, `partially_correct`, `incorrect`, `ridiculous` must have ≥ 1 entry. |
| Non-empty text and explanation | Every answer's `text` and `explanation` must be non-empty strings. |
| Optional tags | If present, `tags` must be a list of non-empty strings; normalized to lowercase. |
| Non-empty subtopic | If a subtopic group is used, its `subtopic` field must be non-empty. |

### CLI Inputs (UC-1 / UC-2)

| Command | Inputs | Description |
|---------|--------|-------------|
| `quizazz generate --input <quiz-dir>` | Path to one quiz directory | Compile one quiz's YAML into a JSON manifest |
| `quizazz generate --all --input <data-root>` | Path to parent of quiz directories | Compile every sibling quiz under the data root |
| `quizazz generate [...] --output <dir>` | Output directory (default `app/src/lib/data/`) | Where compiled manifests are written |
| `quizazz build` | — | Produce the SvelteKit production build (static assets) |
| `quizazz build --standalone <quiz-name>` | Quiz name | Build a standalone single-quiz SPA (UC-1): stages only the named manifest and elides chooser/upload UI |
| `quizazz run [--port N]` | Optional port (default 8000) | Build (if needed), start a local static server, open the browser |

### Runtime Quiz Configuration (UC-1 / UC-2)

| Parameter | Type | Constraints |
|-----------|------|-------------|
| Topic/subtopic selection | Tree selection | One or more nodes from the navigation tree |
| Tag filter | String list (optional) | Zero or more tags; OR logic across selected tags |
| Number of questions | Integer | 1 to filtered pool size |
| Number of answer choices | Integer | 3, 4, or 5 |

### Runtime Manifest Upload (UC-2)

The multi-quiz hub accepts a user-supplied compiled manifest (a JSON file produced by `quizazz generate`). On upload:

1. The file is parsed and validated against the runtime manifest schema.
2. If valid, the quiz is added to the chooser for the current browser session and is immediately launchable.
3. If invalid, a clear error identifies the problem; the quiz is not added.
4. A fresh per-quiz IndexedDB database is created when the upload is first launched.

Uploaded quizzes are **session-only in v1**; they are lost on page reload. Cross-session persistence of uploaded quizzes is a Future Vision item.

### Build-Time Python Library API (UC-3)

Host frameworks integrate with Quizazz at build time via a Python library API importable from `quizazz`:

| Function | Inputs | Description |
|----------|--------|-------------|
| `compile_assessment(yaml_path, base_dir) -> dict` | `yaml_path: Path` to the assessment YAML (relative to `base_dir`), `base_dir: Path` | Parse, validate, and compile one assessment YAML file into a manifest dict ready for JSON serialization |
| `validate_assessment(yaml_path, base_dir) -> list[str]` | Same | Validate without compiling; returns an empty list on success, or a list of human-readable error strings |

Both functions are synchronous, perform no disk writes or server startup, and do no I/O beyond reading the specified YAML file and files it references.

### Embeddable Component Props (UC-3)

The `<QuizBlock>` SvelteKit component accepts:

| Prop | Required | Description |
|------|----------|-------------|
| `manifest` | Yes | The compiled manifest object produced by `compile_assessment` (deserialized from the host's JSON data file) |
| `quizRef` | Yes | A unique string identifying this quiz instance (typically the assessment's ref path in the host's curriculum); used as the progress-tracking key |

In UC-3 v1 the component does **not** accept topic/subtopic scope, question count, or tag-filter props from the host — the manifest *is* the full assessment unit (e.g., a pre-module or post-module 3–5 question set in the consumer context). Richer host-supplied scope is a Future Vision item.

---

## Outputs

### Compiled Quiz Manifest

Each quiz compiles to a single JSON manifest that includes:

- Quiz identity and display metadata.
- The navigation tree structure (directory nodes, topic nodes with `menu_name`/`menu_description`/`quiz_description`, subtopic nodes).
- All questions with their answers, categories, explanations, and tags, keyed by stable IDs for score persistence.

For UC-1 and UC-2 the CLI writes manifests to the builder's configured output directory (default `app/src/lib/data/`), from which the app bundles them at build time. For UC-3 the Python library API returns the manifest as a dict for the host to serialize into its own generated output.

### Quiz Experience (UC-1 / UC-2 / UC-3)

- A sequence of multiple-choice questions, one at a time, with the configured number of labeled (a–e) answer choices.
- Visual feedback for answer selection and for the per-question timer.
- Progress indicator and mid-quiz review access.

### Results Summary (UC-1 / UC-2)

After the final submission, the app displays:

- **Score** — points earned vs. maximum possible (number of questions × 1), expressed as a percentage.
- **Per-question list** — each question with a correct/incorrect indicator.
- **Drill-down review** — each question's full presented answer set with the user's selection highlighted, each answer's category, and each answer's explanation.

In UC-3 the component renders the same results summary and drill-down inline in the host's layout.

### Persistent Data

- A SQLite database per quiz, stored in IndexedDB (via sql.js) and keyed by quiz identity, containing per-question cumulative score and per-session answer history. This is true in all three use cases; the embedded component's IndexedDB is isolated from any host database.

### Build-Time Python Library API Outputs (UC-3)

- `compile_assessment(...)` returns a manifest **dict** ready for JSON serialization by the host.
- `validate_assessment(...)` returns an empty list on success, or a list of human-readable error strings identifying each failure.
- On validation failure, `compile_assessment(...)` raises a specific exception type (`quizazz.ValidationError` or equivalent) carrying the offending file path, a human-readable message, and optional structured detail (question index, field name).

### Embedded Component Completion Event (UC-3)

On quiz completion the `<QuizBlock>` component emits a `complete` event with:

| Field | Type | Description |
|-------|------|-------------|
| `quizRef` | string | The ref passed in as a prop, echoed back |
| `score` | number | Points earned (sum of scored answers) |
| `maxScore` | number | Maximum possible points (= `questionCount`) |
| `questionCount` | number | Total questions presented |

The host decides what to do with this payload (gate the next module on ≥ 80%, write to its own progress database, etc.). Quizazz does not define or enforce gating policy.

---

## Functional Requirements

### FR-1: Build-Time YAML Validation and Compilation (CLI)

The `quizazz generate` command reads YAML files from a quiz directory, validates each against the schema rules (see Inputs), and emits a compiled JSON manifest for that quiz. Two modes:

- **Single quiz** — `quizazz generate --input data/<quiz>/` compiles one quiz.
- **Batch** — `quizazz generate --all --input data/` compiles every sibling quiz under the data root.

If any validation rule is violated, the build fails with a message identifying the file, question index, and specific violation. No manifest is written on failure.

### FR-2: Quiz Chooser and Discovery (UC-2)

On launch of the multi-quiz hub, the app presents a chooser listing all pre-bundled quizzes (manifests present in the build) plus any quizzes uploaded in the current session. Each entry shows the quiz's display metadata; selecting one opens the navigation tree for that quiz. When only one quiz is present (and upload is disabled), the chooser is skipped.

### FR-3: Runtime Manifest Upload (UC-2)

The chooser provides an upload control. On upload:

1. The selected JSON file is parsed and validated against the manifest schema.
2. On success, the quiz is appended to the session's chooser list and can be launched immediately.
3. On failure, a descriptive error is shown and no state changes.
4. The uploaded quiz's database is created fresh when first launched; it is discarded when the browser session ends (v1 scope).

### FR-4: Navigation Tree and Topic Selection (UC-1 / UC-2)

Each quiz presents a navigation tree mirroring its directory/file/subtopic structure:

- **Directory nodes** — expandable groups named after the subdirectory.
- **Topic nodes** — the YAML file's `menu_name` and `menu_description`.
- **Subtopic nodes** — children of a topic when the file uses subtopic groups.
- **Mastery badges** — each node shows a mastery percentage aggregated from the scores of questions within its scope.

The user selects one or more nodes to scope the question pool, then proceeds to configuration.

### FR-5: Mastery Aggregation

Per-topic and per-subtopic mastery percentages are computed at runtime by aggregating the per-question cumulative scores of all questions under a given tree node. Aggregation runs on demand (the question bank is small enough that no caching is required) and updates as scores change.

### FR-6: Quiz Configuration Screen (UC-1 / UC-2)

After topic selection, the user configures:

- **Tag filter** (optional) — a list of tags present in the selected scope. Selecting tags further filters the pool (OR logic). The available question count updates live as tags are toggled.
- **Number of questions** — 1 to the filtered pool size.
- **Number of answer choices** — 3, 4, or 5.

The "Start Quiz" button is disabled if the filtered pool is empty. This screen is not shown in UC-3; the embedded component runs the manifest as-is.

### FR-7: Weighted Random Question Selection

When the quiz starts, the app loads per-question scores, scopes the pool by topic selection and tag filter (UC-1 / UC-2) or takes the full manifest question set (UC-3), and selects the requested number of questions using weighted random sampling without replacement. The weight formula — `weight = max_score − score + 1` — ensures lower-scored questions are drawn more often while guaranteeing every question a nonzero probability.

### FR-8: Answer Presentation

For each presented question:

1. Exactly one answer is randomly drawn from the `correct` category.
2. The remaining slots (answer_count − 1) are filled by random draws from the combined `partially_correct`, `incorrect`, and `ridiculous` pool for that question.
3. The chosen answers are shuffled into random order.
4. Answers are labeled `a`, `b`, `c`, `d`, and (if 5 choices) `e`.

### FR-9: Answer Input

The user selects an answer by pressing the corresponding letter key (`a`–`e`) or clicking anywhere on the answer row. Selection is visually indicated. The user confirms via the Submit button or `Enter`. Submitting without a selection is a no-op.

### FR-10: Deferred Scoring and Answer Changing

Between first selection and submission, the user may change their selection freely. No score is recorded until submission. On submission, the selected answer is scored by category:

| Category | Points |
|----------|--------|
| `correct` | **+1** |
| `partially_correct` | **−2** |
| `incorrect` | **−5** |
| `ridiculous` | **−10** |

The points are added to the question's cumulative score and persisted to IndexedDB, and the session's answer record is updated.

### FR-11: Per-Question Timer

Each question displays the elapsed time since the question was presented. The timer is **informational only** in v1 — it does not cap answer time, penalize slowness, or influence scoring. Future versions may add time-based restrictions or consequences.

### FR-12: Progress Indication

During the quiz, the UI shows a progress bar (percent complete) and a "Question N of M" label, both visible at all times.

### FR-13: Mid-Quiz Review

During a quiz, pressing `Escape` opens a review view listing previously answered questions. The user can open any answered question to see the full presented answer set, their selection, categories, and explanations. Closing the review returns to the current (unanswered) question without altering quiz progress.

### FR-14: Results Summary and Drill-Down

After the final submission, the summary view displays the score percentage, per-question outcome indicators, and a drill-down: clicking any question opens a detail view showing the question, all presented answers (user's selection highlighted), each answer's category and explanation, and a back control. A left/right carousel navigates between adjacent question reviews.

### FR-15: Post-Quiz Actions

In UC-1 / UC-2, from the results summary the user chooses:

- **Retake** — same questions, answers reshuffled; scores accumulate.
- **Start** — return to navigation/configuration for a fresh selection.
- **Quit** — return to navigation; semantically a "done" action, functionally equivalent to Start.

In UC-3, "Retake" may be offered within the component; "Start" and "Quit" are governed by the host layout and are not provided by the component itself.

### FR-16: Database Initialization and Per-Quiz Isolation

Each quiz has its own IndexedDB database, keyed by quiz identity. On first load (or if the database is missing/corrupt):

1. Create the SQLite schema in memory (sql.js).
2. Seed each question's cumulative score to zero.
3. Persist the database to IndexedDB.

On subsequent loads, the database is restored from IndexedDB. Scores from one quiz cannot affect another; the embedded component's databases remain isolated from any host database.

### FR-17: Standalone Single-Quiz SPA (UC-1)

The app supports a standalone build mode where the bundled output contains exactly one quiz and opens directly into that quiz's navigation tree. The chooser and runtime upload UI are elided in this mode. Selected via `quizazz build --standalone <quiz-name>`. All other behavior (nav tree, config, quiz flow, scoring, review, retake) is identical to UC-2.

### FR-18: Python Library API for Build-Time Assessment Compilation (UC-3)

Quizazz exposes a public Python library API under the `quizazz` package:

- `compile_assessment(yaml_path, base_dir) -> dict` — reads the given YAML file, validates it against the question schema, compiles it into a manifest dict, and returns the dict.
- `validate_assessment(yaml_path, base_dir) -> list[str]` — validation without compilation; returns an empty list on success or a list of human-readable error strings.
- `ValidationError` — a specific exception raised by `compile_assessment` on validation failure, carrying the offending file path, a human-readable message, and optional structured detail (question index, field name).

The API is synchronous, performs no disk writes or server startup, does no I/O beyond reading the specified YAML and files it references, and is importable as `from quizazz import compile_assessment, validate_assessment, ValidationError`. The host is responsible for serializing the returned dict (typically to JSON inside its own generated output).

### FR-19: Embeddable `<QuizBlock>` SvelteKit Component (UC-3)

Quizazz ships a SvelteKit component that renders a compiled manifest inline within a host SvelteKit application:

- **Props**: `manifest` (compiled manifest object), `quizRef` (unique instance identifier).
- **Behavior**: presents questions from the manifest one at a time with a configurable answer count (3–5), applies the core scoring, review, and summary flows (FR-7 through FR-14) within the host's layout, and manages its own per-quiz IndexedDB for per-question scores.
- **Event**: emits `complete` on quiz finish with `{quizRef, score, maxScore, questionCount}`. The host consumes this aggregate to update its own progress tracking.
- **Isolation**: self-contained — no external network dependency, no server dependency. The component's IndexedDB is fully isolated from any host database.
- **Theming**: ships self-contained styles for polished default rendering with no host CSS framework setup; exposes CSS custom properties as the universal theming surface; host Tailwind utilities layer additively on top when the host happens to use Tailwind.
- **Keyboard**: FR-9 and FR-13 interactions continue to work when embedded; the component does not capture keys the host expects to handle globally.

---

## Configuration

### Build-Time Configuration (UC-1 / UC-2)

| Setting | Default | Description |
|---------|---------|-------------|
| Input quiz directory | `data/quiz/` | Single-quiz input path |
| Data root (batch mode) | `data/` | Parent of sibling quiz directories |
| Output directory | `app/src/lib/data/` | Where compiled manifests are written |
| Build mode | Multi-quiz hub | UC-1 standalone mode is selected via `quizazz build --standalone <quiz-name>` |

### Build-Time Configuration (UC-3)

Hosts control build-time integration entirely through the Python library API — no Quizazz-level config file is required on the host side. The host supplies `yaml_path` and `base_dir` per call.

### Runtime Configuration

In UC-1 / UC-2, all runtime configuration is through the in-app navigation/configuration screens (FR-4, FR-6). In UC-3, runtime configuration is limited to the `manifest` and `quizRef` props. There are no runtime environment variables or config files in any mode.

---

## Testing Requirements

- **YAML validation** — unit tests covering valid files and every validation-rule violation; file-level metadata and subtopic validation; edge cases (empty file, malformed structure).
- **Manifest generation** — tests verifying the compiled navigation tree matches the directory/file/subtopic hierarchy and that all questions are present with stable IDs.
- **Runtime manifest schema validation** — tests for accepting valid uploaded manifests and rejecting malformed/invalid ones with clear error messages.
- **Scoring** — unit tests for each category's point value and for cumulative score updates.
- **Weighted selection** — statistical tests over many iterations verifying lower-scored questions are drawn more frequently and every question retains nonzero probability.
- **Answer presentation** — tests verifying exactly one correct answer is always included and total count matches configuration.
- **Mastery aggregation** — tests for per-topic and per-subtopic aggregation from per-question scores.
- **Navigation tree scoping** — tests for selection/tag filters correctly scoping the question pool.
- **Deferred scoring** — tests confirming answer changes before submission do not record a score, and submission records exactly one score.
- **Mid-quiz review** — tests confirming review does not alter progress or scoring state.
- **Database isolation and recovery** — tests for per-quiz DB creation, score updates, and recovery from a missing or corrupt database.
- **Keyboard and mouse input** — tests for letter-key selection, Enter-to-submit, Escape-to-review, carousel navigation, and mouse-click equivalents.
- **Python library API (UC-3)** — tests for `compile_assessment` returning a valid manifest for well-formed YAML, raising `ValidationError` for malformed YAML (with file path and structured detail populated), and for `validate_assessment` returning the expected error strings.
- **Embeddable component (UC-3)** — component tests verifying `<QuizBlock>` renders a manifest end-to-end, handles keyboard and mouse input without leaking events, and fires the `complete` event with the correct `{quizRef, score, maxScore, questionCount}` payload shape.
- **Standalone build (UC-1)** — tests verifying `quizazz build --standalone <name>` produces a build that elides chooser/upload UI and opens directly to the single quiz.

---

## Security and Compliance Notes

- No user-identifying or sensitive data is collected or stored by Quizazz.
- All data lives in the user's browser; no network requests after initial page load.
- The sql.js WASM binary is bundled with the app (no CDN dependency).
- Uploaded manifests are parsed and schema-validated client-side; malformed input is rejected rather than executed.
- In UC-3, the host is responsible for any user identity or session semantics; Quizazz itself remains anonymous, and its IndexedDB data is never shared with the host database.

---

## Performance Notes

- Question banks are expected to range from tens to low hundreds of questions per quiz. No pagination or lazy loading is required.
- sql.js operations are synchronous and fast at this data volume.
- IndexedDB persistence occurs after each score update to minimize data loss on unexpected close.
- Mastery aggregation runs on demand without caching; recomputation cost is negligible at the expected scale.
- The Python library API's `compile_assessment` / `validate_assessment` are expected to run in under 100 ms per typical assessment YAML on modern hardware; hosts may call them in tight build loops without concern.

---

## Acceptance Criteria

The project is complete for v1 when:

1. An author can write YAML questions, run `quizazz generate`, `quizazz build`, and `quizazz run`, and take the resulting quiz in a browser.
2. Multiple quiz directories under `data/` each compile to a manifest and are all selectable from the chooser (UC-2).
3. The builder supports both single-quiz and `--all` batch modes and fails clearly on any validation violation.
4. The app can also be built as a standalone single-quiz SPA via `quizazz build --standalone <quiz-name>` that opens directly into one specific quiz with the chooser/upload UI hidden (UC-1).
5. A user can upload an externally compiled quiz manifest at runtime and immediately take that quiz in the current session (UC-2).
6. Each quiz SPA displays a navigation tree with per-topic/subtopic mastery scores.
7. Questions are presented with weighted random selection that favors lower-scored questions while guaranteeing every question a nonzero probability.
8. Each presented question shows exactly one correct answer among the configured number of choices.
9. Answers can be selected via keyboard (letter keys) or mouse, may be changed until submit, and are scored on submit.
10. A per-question timer displays elapsed time on each question.
11. Scores persist across browser sessions, isolated per quiz.
12. The results summary shows score percentage, per-question outcomes, and drill-down with explanations.
13. Retake, Start, and Quit post-quiz actions work as specified in UC-1 / UC-2.
14. Tag filtering correctly restricts the question pool and the question-count slider adjusts to the filtered pool size.
15. Mid-quiz review is reachable via `Escape`, lets the user inspect answered questions, and returns without altering progress.
16. A host framework can `from quizazz import compile_assessment, validate_assessment, ValidationError`, call `compile_assessment(yaml_path, base_dir)` to produce a manifest dict for well-formed YAML, and catch `ValidationError` with file path and structured detail for malformed YAML (UC-3).
17. A host SvelteKit application can import `<QuizBlock>` from `@pointmatic/quizazz`, pass `manifest` and `quizRef` props, render a quiz end-to-end inline in its own layout, and receive a `complete` event with `{quizRef, score, maxScore, questionCount}` on finish (UC-3).
18. `quizazz` is installable from PyPI and `@pointmatic/quizazz` is installable from npm (or bundled into the host's SvelteKit template), both following semantic versioning keyed to the compiled manifest schema.
19. The UI is minimalist, modern, responsive, and keyboard-navigable end-to-end.

---

## Future Vision

Directional items not in v1. These inform architectural decisions but do not block shipping.

- **LLM-assisted question generation pipeline (UC-4)** — A `python/` Python toolchain that takes source material and uses LLM APIs to generate validated YAML question banks. Manual prompt recipes (see [`llm_question_generation_manual.md`](llm_question_generation_manual.md)) exist today; a codified, repeatable pipeline is future.
- **Answer-length normalization** — Require short and long variants per answer and present a uniform length profile (all short, all long, or random) per question to eliminate the length-based guessing signal.
- **Post-quiz quality feedback loop** — Per-quiz star ratings and per-question complaint signals feeding back into question revision workflows.
- **Persisted runtime uploads** — Cross-session persistence of user-uploaded quizzes (currently session-only in v1).
- **Extended host integration surface (beyond UC-3 minimum)** — Host-supplied scope/question-count/tag-filter props on `<QuizBlock>`; per-question outcome streaming in the `complete` event (or a separate stream event); pre-launch mastery queries; bi-directional messaging for richer host-directed flows.
- **Score decay and spaced repetition** — Scores drift toward zero over time so mastered questions periodically resurface.
- **Session history and analytics** — Track quiz sessions over time with trend charts and improvement metrics.
- **Cross-quiz dashboard** — A landing page aggregating stats across all deployed quizzes.
- **`api/` FastAPI backend** — Optional server component for user auth, centralized score storage, LLM generation triggers, and automated redeployment of static apps with updated question banks.
