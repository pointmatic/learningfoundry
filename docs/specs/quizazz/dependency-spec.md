# dependency-spec.md — quizazz (as consumed by learningfoundry)

This document defines what learningfoundry **requires** from quizazz — the contract between the two projects. It does not redefine quizazz's standalone features (see `features.md` and `tech_spec.md` in this directory for the full quizazz specification). Instead, it specifies the subset of quizazz functionality that learningfoundry depends on, the integration interface, data flow, and constraints.

---

## Role in learningfoundry

quizazz is the **assessment content provider**. learningfoundry's pipeline invokes quizazz at build time to compile assessment YAML files into renderable quiz manifests. These manifests are embedded in the generated SvelteKit application, where quizazz's frontend components handle quiz delivery, scoring, and review.

### Integration Points

| learningfoundry Stage | quizazz Role |
|----------------------|--------------|
| **Content resolution** (Python, build time) | Validate and compile assessment YAML → JSON manifest |
| **SvelteKit frontend** (TypeScript, runtime) | Render inline quizzes, handle scoring, persist results |
| **Progress tracking** (runtime) | Report quiz completion event (score, max_score) to learningfoundry's progress database |

---

## Build-Time Requirements (Python API)

### BR-1: Assessment Compilation API

quizazz must expose a Python API that learningfoundry can call during content resolution to compile a single assessment YAML file into a manifest dict.

**Required interface:**

```python
def compile_assessment(yaml_path: Path, base_dir: Path) -> dict:
    """
    Validate and compile a single assessment YAML file into a renderable manifest.

    Args:
        yaml_path: Path to the assessment YAML file (relative to base_dir).
        base_dir: Root directory for resolving relative paths within the YAML.

    Returns:
        A dict representing the compiled quiz manifest, suitable for JSON
        serialization and consumption by the quizazz frontend component.

    Raises:
        quizazz.ValidationError: If the YAML file fails validation (missing
            fields, insufficient answers, etc.). The error must include:
            - The file path that failed.
            - A human-readable description of the validation failure.
            - The specific field or question index that caused the failure.
    """
```

**Behavior:**
1. Read and parse the YAML file at `base_dir / yaml_path`.
2. Validate against quizazz's question schema (minimum answers, category coverage, non-empty fields, etc.).
3. Compile the validated content into a manifest dict containing the navigation tree, question list, and answer data.
4. Return the manifest dict. learningfoundry serializes it to JSON and embeds it in the SvelteKit app as a data file.

**Constraints:**
- The function must be importable from the `quizazz_builder` package (e.g., `from quizazz_builder import compile_assessment`).
- The function must be synchronous (no async).
- The function must not perform any I/O beyond reading the specified YAML file and any files it references.
- The function must not write to disk, start servers, or have side effects.

### BR-2: Validation-Only API

quizazz must expose a validation-only function that checks an assessment YAML file without producing a full manifest. learningfoundry uses this during the `validate` CLI command.

**Required interface:**

```python
def validate_assessment(yaml_path: Path, base_dir: Path) -> list[str]:
    """
    Validate an assessment YAML file without compiling.

    Returns:
        An empty list if valid, or a list of human-readable error strings.
    """
```

### BR-3: Error Contract

quizazz validation errors must be catchable as a specific exception type (`quizazz.ValidationError` or similar) that learningfoundry wraps in its own `IntegrationError`. The exception must carry:

- **file_path**: The assessment file that failed.
- **message**: Human-readable description.
- **detail**: Optional structured detail (question index, field name).

---

## Runtime Requirements (SvelteKit Component)

### RR-1: Embeddable Quiz Component

quizazz must provide a SvelteKit component (or set of components) that learningfoundry can embed in its generated pages to render a quiz from a compiled manifest.

**Required interface:**

```svelte
<QuizBlock
  manifest={quizManifest}
  quizRef={refPath}
  on:complete={handleQuizComplete}
/>
```

**Props:**
- `manifest` — The compiled quiz manifest dict (deserialized from the JSON data file).
- `quizRef` — A unique string identifying this quiz instance (the assessment ref path from the curriculum YAML). Used as the key for progress tracking.

**Events:**
- `complete` — Fired when the learner finishes the quiz. Event detail must include:

```typescript
interface QuizCompleteEvent {
  quizRef: string;        // The ref path passed in
  score: number;          // Points earned (sum of correct answers)
  maxScore: number;       // Maximum possible score (number of questions)
  questionCount: number;  // Total questions in the quiz
}
```

**Behavior:**
1. Present questions one at a time from the manifest, with configurable answer count (3–5).
2. Score answers using quizazz's weighted scoring model (correct: +1, partially_correct: −2, incorrect: −5, ridiculous: −10).
3. Display a results summary after the last question.
4. Fire the `complete` event with aggregate score data.
5. Manage its own internal state (current question, session answers, review navigation).

**Constraints:**
- The component must be self-contained — no external network requests, no server dependency.
- The component manages its own per-quiz SQLite database for detailed question-level scoring (as per quizazz's existing design). learningfoundry's progress database only stores the aggregate score reported via the `complete` event.
- The component must accept Tailwind CSS utility classes or expose CSS custom properties for theme integration with learningfoundry's frontend.

### RR-2: Database Isolation

quizazz's per-quiz IndexedDB databases (e.g., `quizazz-{quizName}`) must remain separate from learningfoundry's progress database. The two systems share no tables. learningfoundry writes quiz summary data to its own `quiz_scores` table only when the `complete` event fires.

### RR-3: Keyboard Interaction

The embedded quiz component must support keyboard-first interaction (letter keys for answer selection, Enter to submit) as specified in quizazz's own features (FR-6). This must work correctly when embedded within learningfoundry's page layout without keyboard event conflicts.

---

## Data Flow Summary

```
Build time (Python):
  curriculum.yml
    → content resolution encounters `type: quiz, source: quizazz, ref: ...`
    → learningfoundry calls quizazz_builder.compile_assessment(ref, base_dir)
    → receives manifest dict
    → serializes to JSON in generated SvelteKit project

Runtime (SvelteKit):
  LessonView renders QuizBlock component with manifest + quizRef
    → quizazz component handles quiz delivery, scoring, review
    → quizazz manages its own IndexedDB for per-question scores
    → on quiz completion, fires `complete` event
    → learningfoundry writes {quizRef, score, maxScore} to its quiz_scores table
    → progress dashboard reads quiz_scores for module-level display
```

---

## Package Distribution

| Concern | Value |
|---------|-------|
| **Python package** | `quizazz-builder` on PyPI |
| **SvelteKit component** | Published as an npm package (e.g., `@pointmatic/quizazz`) or bundled in learningfoundry's SvelteKit template |
| **learningfoundry dependency** | Optional: `pip install learningfoundry[quizazz]` installs `quizazz-builder` |

---

## Versioning and Compatibility

- learningfoundry pins `quizazz-builder>=0.1` as an optional dependency.
- The manifest dict schema is the versioning boundary. Breaking changes to the manifest structure require a major version bump in `quizazz-builder` and a corresponding update in learningfoundry's `QuizazzProvider`.
- The SvelteKit component and the Python builder must agree on the manifest schema. learningfoundry does not interpret the manifest contents — it passes the dict through opaquely.

---

## Testing Contract

| Test | Owner | What is tested |
|------|-------|----------------|
| `compile_assessment` returns valid manifest for well-formed YAML | quizazz | Unit test in quizazz repo |
| `compile_assessment` raises `ValidationError` for malformed YAML | quizazz | Unit test in quizazz repo |
| learningfoundry's `QuizazzProvider` delegates correctly to `compile_assessment` | learningfoundry | Unit test with mocked `quizazz_builder` |
| learningfoundry wraps `ValidationError` in `IntegrationError` with block location | learningfoundry | Unit test |
| `QuizBlock` component renders manifest and fires `complete` event | quizazz | Component test in quizazz repo |
| learningfoundry's `QuizBlock` integration writes score to `quiz_scores` table | learningfoundry | Integration test |
