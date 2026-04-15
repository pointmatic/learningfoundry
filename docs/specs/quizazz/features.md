# features.md — Quizazz (SvelteKit + Node + Python)

## Overview

This document defines **what** Quizazz does — its requirements, inputs, outputs, and behavior — without specifying implementation details. For architecture and module design, see [`tech_spec.md`](tech_spec.md). For the phased implementation plan, see [`stories.md`](stories.md). For the multi-quiz design rationale, see [`multi_quiz_features.md`](multi_quiz_features.md).

---

## Project Goal

Quizazz is a browser-based study tool that quizzes users on their understanding of a topic. Questions and categorized answers are authored in YAML, validated and compiled at build time, and presented as an interactive multiple-choice quiz in a modern single-page application. User performance is tracked in a client-side SQLite database (via sql.js/WASM), and a weighted-random algorithm prioritizes questions the user struggles with most.

Quizazz supports **multiple independent quizzes**. Each quiz is a directory of YAML files under `data/`, compiled into its own self-contained SPA with its own database. A default quiz (`data/quiz/`) ships with the repository as a getting-started example; users create additional quizzes as sibling directories.

The repository is organized as a monorepo with two primary workspaces:

| Directory | Purpose |
|-----------|--------|
| `app/` | SvelteKit quiz UI, runtime, and Node build tooling |
| `builder/` | Python-based quiz generation and YAML validation tooling |
| `data/` | Quiz directories — each subdirectory is an independent quiz package |

This separation keeps the runtime app independent from the authoring/generation toolchain and positions the project for future expansion (see [Future Vision](#future-vision)).

### Core Requirements

1. **Multi-quiz support** — Each subdirectory under `data/` is an independent quiz. Each quiz compiles to its own SPA with its own database. The builder supports compiling a single quiz or all quizzes in batch.
2. **YAML question bank** — Questions and answers are defined in YAML files with per-file metadata (`menu_name`, `menu_description`, `quiz_description`). Questions may optionally be grouped under subtopics within a file.
3. **Answer categorization** — Each answer belongs to one of four categories: `correct`, `partially_correct`, `incorrect`, or `ridiculous`.
4. **Navigation tree** — Each quiz SPA displays a navigation tree mirroring the directory structure and YAML file metadata. The user selects topics/subtopics to scope the question pool before configuring a quiz.
5. **Score visibility** — The navigation tree displays per-topic and per-subtopic mastery percentages, computed at runtime by aggregating per-question scores.
6. **Interactive quiz UI** — A minimalistic, modern web interface presents multiple-choice questions one at a time.
7. **Weighted question selection** — Questions are drawn from the pool using weighted random selection, where lower scores (including negative) are more likely to be drawn.
8. **Scoring and persistence** — Each answer is scored and recorded in a client-side SQLite database that persists across sessions via IndexedDB. Each quiz has its own isolated database.
9. **Results summary** — After completing a quiz, the user sees a summary with score percentage, per-question results, and the ability to review each question with explanations.
10. **Tags and filtering** — Questions may optionally include tags. The configuration screen lets users filter the question pool by tag before starting a quiz.

### Operational Requirements

11. **Build-time validation** — The build script must validate YAML files and fail with clear error messages if any question does not meet the minimum answer requirements.
12. **Graceful error handling** — Runtime errors (e.g., corrupt database) should display a user-friendly message, not a blank screen or stack trace.
13. **Database initialization** — On first launch (or if the database is missing), the app automatically creates the schema and seeds initial scores.

### Quality Requirements

14. **Deterministic shuffling** — Answer order is randomized per question presentation, but the randomization is not seeded (true randomness each time).
15. **Fair question selection** — The weighted random algorithm must ensure all questions have a nonzero probability of being selected, regardless of score.

### Usability Requirements

16. **Keyboard-first interaction** — Users can answer questions by pressing `a`–`e` to select and `Enter` to submit. Mouse/touch interaction is equally supported.
17. **Progress indication** — A progress bar and "question N of M" label are always visible during the quiz.
18. **Quiz configuration** — Before starting, the user selects topics/subtopics from the navigation tree, then configures the number of questions (1 to max) and the number of answer choices (3, 4, or 5).
19. **Post-quiz navigation** — From the results summary, clicking a question navigates to a detailed review of that question. A "← Back" button returns to the summary. Carousel navigation (`←`/`→`) moves between reviewed questions.
20. **Mid-quiz review** — During a quiz, the user can press `Escape` to view previously answered questions, review any of them with full explanations, and return to the current unanswered question.
21. **Post-quiz actions** — After completing a quiz, the user can:
    - **Retake** — Same questions and answers, reshuffled.
    - **Start** — New quiz with fresh question selection (returns to navigation/configuration screen).
    - **Quit** — Returns to the navigation/configuration screen.

### Non-Goals

- **User accounts or authentication** — This is a single-user, local-first app.
- **Server-side persistence** — All data lives in the browser (IndexedDB-backed SQLite).
- **Real-time multiplayer** — No collaborative or competitive features.
- **Question editing in the UI** — Questions are authored in YAML files and compiled at build time.
- **Mobile native app** — Browser-only; responsive design is acceptable but native wrappers are out of scope.
- **Score decay / spaced repetition** — Deferred to a future version.
- **Session history / stats over time** — Deferred to a future version.
- **LLM-powered quiz generation** — The `builder/` directory will eventually use LLM APIs to generate questions from source material. Out of scope for v1.
- **FastAPI backend** — A future `api/` directory could provide server-side auth, results aggregation, quiz generation triggers, and automated deployment of updated static apps. Out of scope for v1.
- **Multi-user / server-side persistence** — Deferred until the FastAPI backend is introduced.

---

## Inputs

### Quiz Directory Layout

Each quiz is a directory under `data/`. The directory may contain any number of `.yaml` files organized in any hierarchy of subdirectories:

```
data/
  quiz/                        ← default quiz (ships with repo)
    sample.yaml
    advanced/
      topic-a.yaml
      topic-b.yaml
  data-engineering/            ← user-created quiz
    fundamentals.yaml
    pipelines/
      batch.yaml
      streaming.yaml
```

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
              explanation: "Atlantis is a mythical city and does not exist."
            - text: "The Moon"
              explanation: "The Moon is not a city, let alone a capital."
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
| `menu_name` | Yes | Display name shown in the quiz navigation tree |
| `menu_description` | No | Short blurb shown alongside the menu entry |
| `quiz_description` | No | Longer description shown when the user selects this topic |
| `questions` | Yes | List of questions or subtopic groups |

**Subtopic groups** are optional. The `questions` list can contain bare `Question` objects, `SubtopicGroup` objects (with `subtopic` and `questions` fields), or a mix of both.

**Validation rules (enforced at build time):**

| Rule | Description |
|------|-------------|
| Non-empty `menu_name` | Each YAML file must have a non-empty `menu_name` field. |
| Minimum 5 answers | Each question must have at least 5 answers total across all categories. |
| At least 1 correct | Each question must have at least one answer in the `correct` category. |
| At least 1 in each non-correct category | Each question must have at least one `partially_correct`, one `incorrect`, and one `ridiculous` answer. |
| Exactly 1 correct in any presented set | When the app presents a question, exactly one of the shown answers will be `correct`. The remaining shown answers are drawn from the other categories. |
| Non-empty text and explanation | Every answer must have a non-empty `text` and `explanation` field. |
| Non-empty question | The `question` field must be a non-empty string. |
| Optional tags | The `tags` field is optional. If present, it must be a list of non-empty strings. Tags are case-insensitive and normalized to lowercase. |
| Non-empty subtopic | If a subtopic group is used, the `subtopic` field must be a non-empty string. |

### Quiz Configuration (Runtime)

| Parameter | Type | Constraints |
|-----------|------|-------------|
| Topic/subtopic selection | Tree selection | One or more topics/subtopics from the navigation tree; scopes the question pool |
| Number of questions | Integer | 1 to total number of questions in the selected scope |
| Number of answer choices | Integer | 3, 4, or 5 |
| Tag filter | String list (optional) | Zero or more tags; when set, only questions matching **any** selected tag are included in the pool |

---

## Outputs

### Quiz Experience

- A sequence of multiple-choice questions presented one at a time.
- Each question shows the question text and the configured number of answer choices (labeled a–e).
- After submission, the user's answer is scored and recorded.

### Results Summary

After the final question, the app displays:

- **Score percentage** — Points earned as a percentage of the maximum possible (i.e., number of questions, since +1 per correct answer is the max).
- **Question list** — Each question with a correct/incorrect indicator.
- **Drill-down** — Clicking a question shows the question, the user's selected answer (highlighted), and the explanation for each presented answer.

### Persistent Data

- A SQLite database per quiz (stored in IndexedDB via sql.js, keyed by quiz directory name) containing:
  - Per-question cumulative score.
  - Per-question answer history for the current quiz session (to support retake and review).

---

## Functional Requirements

### FR-1: Build-Time YAML Validation and Compilation

The builder reads all `.yaml` files from a quiz directory, validates each file's metadata and questions against the rules in the Inputs section, and outputs a compiled JSON manifest for that quiz. The manifest includes the navigation tree structure (directories, topics, subtopics) and all compiled questions. The builder supports two modes:

- **Single quiz**: `--input data/quiz/ --output app/build/quiz/` — compiles one quiz directory.
- **All quizzes**: `--all --input data/ --output app/build/` — compiles every subdirectory of `data/` as a separate quiz.

If any validation rule is violated, the build fails with a descriptive error message identifying the file, question index, and the specific violation.

### FR-2: Navigation Tree and Topic Selection

On launch, the quiz SPA presents a **navigation tree** that mirrors the directory structure of the quiz's YAML files:

- **Directory nodes** — expandable groups named after the subdirectory.
- **Topic nodes** — leaf or intermediate nodes showing the YAML file's `menu_name` and `menu_description`.
- **Subtopic nodes** — child nodes under a topic, if the file uses subtopic groups.
- **Score indicators** — each node displays a mastery percentage computed from the per-question scores of all questions within that node's scope.

The user selects one or more topics/subtopics to scope the question pool, then proceeds to the configuration screen.

### FR-3: Quiz Configuration Screen

After selecting topics/subtopics, the user configures:
- **Tag filter** (optional) — A list of all available tags within the selected scope is displayed. The user can select zero or more tags to further filter the question pool (OR logic). The available question count updates dynamically as tags are toggled.
- **Number of questions** (slider or number input, range 1 to filtered pool size).
- **Number of answer choices** (radio buttons: 3, 4, or 5).

A "Start Quiz" button begins the quiz. The button is disabled if the configuration is invalid (e.g., filtered pool is empty).

### FR-4: Weighted Random Question Selection

When a quiz starts, the app loads all question scores from the database. The question pool is scoped to the selected topics/subtopics, then further filtered by tags if active. Questions are then selected using weighted random sampling without replacement:
- Weight is derived from the score such that lower scores yield higher weights.
- All questions in the filtered pool must have a nonzero probability of selection.
- Selection continues until the requested number of questions is reached (or the pool is exhausted).

### FR-5: Answer Selection and Presentation

For each presented question:
1. Exactly one answer is randomly chosen from the `correct` category.
2. The remaining answer slots (answer_count − 1) are filled by randomly choosing from the combined pool of `partially_correct`, `incorrect`, and `ridiculous` answers for that question.
3. The selected answers are shuffled into a random order.
4. Answers are labeled sequentially: a, b, c, d (and e if 5 choices).

### FR-6: Answer Input

The user selects an answer by:
- Pressing the corresponding letter key (`a`–`e`), which highlights the answer, OR
- Clicking anywhere on the answer row (text, radio button, or surrounding area), which highlights the answer.

Selection is visually indicated (e.g., highlighted background, filled radio button). The user confirms by clicking the "Submit" button or pressing `Enter`. Submitting without a selection does nothing.

### FR-7: Scoring

Upon submission, the selected answer is scored based on its category:

| Category | Points |
|----------|--------|
| `correct` | +1 |
| `partially_correct` | −2 |
| `incorrect` | −5 |
| `ridiculous` | −10 |

The score is added to the question's cumulative score in the database. The answer and its category are recorded for the current session (for review purposes).

### FR-8: Progress Indication

During the quiz, the UI displays:
- A progress bar showing percent completion (questions answered / total questions).
- A label: "Question N of M" where N is the current question number and M is the total.

### FR-9: Results Summary

After the last question is submitted, the app displays:
- **Score**: points earned / maximum possible points (number of questions × 1), shown as a percentage.
- **Question list**: each question with a visual indicator (✓ or ✗) for correct/incorrect.
- Clicking a question navigates to a **detail view** showing:
  - The question text.
  - All presented answers with the user's selection highlighted.
  - The explanation for each answer.
  - The category of each answer (correct, partially correct, incorrect, ridiculous).
  - A "← Back" button to return to the summary.

### FR-10: Post-Quiz Actions

From the results summary, the user can:
- **Retake** — Restart the quiz with the same questions and answers, but with answer order reshuffled. Scores are recorded again (cumulative).
- **Start** — Return to the navigation tree to start a fresh quiz (new topic/question selection).
- **Quit** — Return to the navigation tree (same as Start, but semantically "I'm done").

Note: "Quit" and "Start" both navigate to the navigation tree. "Quit" is provided as a distinct label for user intent clarity.

### FR-11: Database Initialization

Each quiz has its own IndexedDB database, keyed by the quiz directory name (e.g., `quizazz-quiz`, `quizazz-data-engineering`). On first load (or if the database is absent/corrupt):
1. Create the SQLite database in memory (sql.js).
2. Create the required tables.
3. Seed each question with an initial score of 0.
4. Persist the database to IndexedDB.

On subsequent loads, the database is restored from IndexedDB. Database isolation ensures scores from one quiz never affect another.

---

## Configuration

### Build-Time Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Quiz directory | `data/quiz/` | Path to a single quiz directory (default quiz). |
| Data root | `data/` | Parent directory containing all quiz directories (used with `--all`). |
| Output directory | `app/build/` | Where compiled quiz SPAs are written. Each quiz gets a subdirectory matching its directory name. |

### Runtime Configuration

All runtime configuration is done through the quiz configuration screen (FR-2). There are no environment variables or config files at runtime.

---

## Testing Requirements

- **YAML validation**: Unit tests covering valid files, each individual validation rule violation, file-level metadata validation, subtopic validation, and edge cases (empty file, duplicate questions).
- **Manifest generation**: Tests verifying the compiled navigation tree structure matches the directory/file/subtopic hierarchy.
- **Scoring logic**: Unit tests for each answer category's point value.
- **Weighted selection**: Tests verifying that lower-scored questions are selected more frequently over many iterations.
- **Answer presentation**: Tests verifying exactly one correct answer is always included and total answer count matches configuration.
- **Navigation tree**: Tests for topic/subtopic selection scoping the question pool correctly.
- **Score aggregation**: Tests for per-topic and per-subtopic mastery computation from question-level scores.
- **UI interaction**: Tests for keyboard input (letter keys, Enter) and click interaction.
- **Database isolation**: Tests for per-quiz database initialization, score updates, and recovery from missing database.

---

## Security and Compliance Notes

- No sensitive data is processed or stored.
- The app runs entirely in the browser with no network requests after initial page load.
- sql.js WASM binary is bundled with the app (no CDN dependency).

---

## Performance Notes

- The question bank is expected to be small (tens to low hundreds of questions). No pagination or lazy loading is needed.
- sql.js operations are synchronous and fast for this data volume.
- IndexedDB persistence happens after each score update to minimize data loss risk.

---

## Acceptance Criteria

The project is complete when:

1. A user can author questions in YAML with file-level metadata and optional subtopics, build the app, and take a quiz in the browser.
2. Multiple quiz directories under `data/` each compile to independent SPAs.
3. The builder supports single-quiz and batch (`--all`) compilation modes.
4. The build fails with clear errors if YAML validation rules are violated.
5. Each quiz SPA displays a navigation tree with per-topic/subtopic mastery scores.
6. Questions are presented with weighted random selection favoring lower-scored questions, scoped to the user's topic/subtopic selection.
7. Each question shows exactly one correct answer among the configured number of choices.
8. Answers can be selected via keyboard (letter keys) or mouse click, and submitted via Enter or Submit button.
9. Scores are persisted across browser sessions, isolated per quiz.
10. The results summary shows score percentage, per-question results, and drill-down with explanations.
11. Retake and Start actions work as specified.
12. The UI is minimalistic, modern, and responsive.
13. Tag filtering on the config screen correctly restricts the question pool, and the question count slider adjusts to the filtered pool size.

---

## Future Vision

This section captures directional thinking for future versions. These items are not in scope for the current roadmap but inform architectural decisions.

- **`builder/` — LLM-powered quiz generation (Python)**: A Python toolchain that takes source material (documents, notes, textbooks) and uses LLM APIs to generate well-structured YAML question files. This is why `builder/` exists as a separate workspace and why YAML validation lives in Python.
- **`api/` — FastAPI backend**: A server component that could provide user authentication, centralized score/results storage, LLM quiz generation triggers, and automated redeployment of the static app with updated question banks.
- **Score decay / spaced repetition**: Scores drift toward 0 over time so mastered questions periodically resurface.
- **Session history and analytics**: Track quiz sessions over time with trend charts and improvement metrics.
- **Cross-quiz dashboard**: A landing page that lists all deployed quizzes with aggregate stats.
