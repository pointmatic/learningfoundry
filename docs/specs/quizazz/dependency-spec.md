# dependency-spec.md — quizazz (as consumed by learningfoundry)

This document defines what learningfoundry **requires** from quizazz — the contract between the two projects. It does not redefine quizazz's standalone features (see `features.md` and `tech_spec.md` in this directory for the full quizazz specification). Instead, it specifies the subset of quizazz functionality that learningfoundry depends on, the integration interface, data flow, and constraints.

---

## Role in learningfoundry

quizazz is the **assessment content provider**. learningfoundry's pipeline invokes quizazz at build time to compile assessment YAML files into renderable manifests. These manifests are embedded in the generated SvelteKit application, where quizazz's frontend component (`<QuizBlock>`) handles assessment delivery, scoring, and review.

### Integration Points

| learningfoundry Stage | quizazz Role |
|----------------------|--------------|
| **Content resolution** (Python, build time) | Validate and compile assessment YAML → JSON manifest |
| **SvelteKit frontend** (TypeScript, runtime) | Render inline assessments via `<QuizBlock>`, handle scoring, persist results |
| **Progress tracking** (runtime) | Report assessment completion event (score, max_score) to learningfoundry's progress database |

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
4. Return the manifest dict. learningfoundry's `QuizazzProvider` adapter relabels the top-level `quizName` key to `assessmentName` (see "Manifest Wire-Format Relabel" under RR-1), then serializes the result to JSON and embeds it in the SvelteKit app as a data file.

**Constraints:**
- The function must be importable from the `quizazz` package (e.g., `from quizazz import compile_assessment`).
- The function must be synchronous (no async).
- The function must not perform any I/O beyond reading the specified YAML file and any files it references.
- The function must not write to disk, start servers, or have side effects.
- **Path escape:** `yaml_path` must resolve under `base_dir`. quizazz raises `quizazz.ValidationError` if the resolved path escapes the `base_dir` tree (e.g., `../../etc/passwd`). learningfoundry relies on this so curriculum YAML cannot reference assessment files outside the curriculum source tree.

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

### RR-1: Embeddable Assessment Component

quizazz must provide a SvelteKit component (or set of components) that learningfoundry can embed in its generated pages to render an assessment from a compiled manifest. The component name (`<QuizBlock>`) is preserved on the vendor surface — see the project-essentials note "Vendor terminology stops at the vendor boundary" for the rationale.

**Required interface:**

```svelte
<QuizBlock
  manifest={assessmentManifest}
  quizRef={refPath}
  oncomplete={handleAssessmentComplete}
/>
```

**Props:**
- `manifest` — The compiled assessment manifest dict (deserialized from the JSON data file, after `QuizazzProvider` has relabeled `quizName` → `assessmentName`).
- `quizRef` — A unique string identifying this assessment instance (the assessment ref path from the curriculum YAML). Used as the key for progress tracking. The prop name is part of the vendor surface and kept as `quizRef`.

**Events:**
- `complete` — Fired when the learner finishes the assessment. Both the Svelte 5 callback-prop form (`oncomplete={handler}`) and a legacy `CustomEvent('complete')` dispatch are supported; the callback-prop form is canonical. Event detail must include:

```typescript
interface AssessmentCompleteEvent {
  quizRef: string;        // The ref path passed in (vendor prop name preserved)
  score: number;          // Points earned (sum of correct answers)
  maxScore: number;       // Maximum possible score (number of questions)
  questionCount: number;  // Total questions in the assessment
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
- The component manages its own per-assessment SQLite database for detailed question-level scoring (as per quizazz's existing design). learningfoundry's progress database only stores the aggregate score reported via the `complete` event.
- The component must accept Tailwind CSS utility classes or expose CSS custom properties for theme integration with learningfoundry's frontend.

#### RR-1a: Manifest Wire-Format Relabel

quizazz emits a manifest whose top-level identifier key is `quizName: string` — that is the vendor's name for its core concept and ships unchanged on the vendor wire format. learningfoundry's downstream `AssessmentManifest` TypeScript interface (consumed by the SvelteKit frontend) uses `assessmentName: string` to stay in learningfoundry's domain vocabulary.

The single point of translation is **`QuizazzProvider.compile_assessment()`** in [`src/learningfoundry/integrations/quizazz.py`](../../../src/learningfoundry/integrations/quizazz.py): it calls `quizazz.compile_assessment(...)`, then relabels `quizName` → `assessmentName` in the returned dict before learningfoundry serializes it into `curriculum.json`. quizazz itself does **not** need to rename anything — the relabel is learningfoundry's responsibility.

Downstream consumers (TypeScript types, SvelteKit components, `curriculum.json`) must never see `quizName`. If they do, the relabel layer regressed.

### RR-2: Database Isolation

quizazz's per-assessment IndexedDB databases (e.g., `quizazz-{quizName}` — vendor-internal naming preserved) must remain separate from learningfoundry's progress database. The two systems share no tables. learningfoundry writes assessment summary data to its own `assessment_scores` table only when the `complete` event fires.

### RR-3: Keyboard Interaction

The embedded assessment component must support keyboard-first interaction (letter keys for answer selection, Enter to submit) as specified in quizazz's own features (FR-6). This must work correctly when embedded within learningfoundry's page layout without keyboard event conflicts.

### RR-4: Host Setup

A SvelteKit host that mounts `<QuizBlock>` must satisfy three setup conditions, otherwise the component fails to render correctly or the bundler fails to resolve its assets:

1. **Stylesheet import.** The host must import quizazz's bundled stylesheet exactly once (typically in the root `+layout.svelte` or the app entry):
   ```ts
   import '@pointmatic/quizazz/styles.css';
   ```
   Without this, `<QuizBlock>` renders unstyled.

2. **Disable SSR on routes that mount `<QuizBlock>`.** quizazz uses browser-only APIs (IndexedDB, the WASM-loaded `sql.js` runtime). Any route that mounts the component must opt out of server-side rendering:
   ```ts
   // +page.ts or +layout.ts
   export const ssr = false;
   ```
   learningfoundry's generated SvelteKit app is already configured `ssr = false` globally, so this condition is satisfied by default for in-tree consumers — but a downstream host integrating `<QuizBlock>` into a partial-SSR app must scope the opt-out per route.

3. **Vite-based build.** quizazz imports its WASM asset via `import wasmUrl from '...?url'` — a Vite-specific suffix that returns the asset's emitted URL. Non-Vite bundlers (webpack, esbuild standalone, Rollup without `@rollup/plugin-url`) will not resolve the `?url` import and the build fails. SvelteKit ships Vite by default, so this is satisfied for the standard scaffold.

---

## Data Flow Summary

```
Build time (Python):
  curriculum.yml
    → content resolution encounters `type: assessment, source: quizazz, ref: ...`
    → learningfoundry's QuizazzProvider calls quizazz.compile_assessment(ref, base_dir)
    → receives manifest dict (top-level key: `quizName`)
    → QuizazzProvider relabels `quizName` → `assessmentName` (RR-1a)
    → serializes to JSON in generated SvelteKit project

Runtime (SvelteKit):
  LessonView renders QuizBlock component with manifest + quizRef
    → quizazz component handles assessment delivery, scoring, review
    → quizazz manages its own IndexedDB for per-question scores
    → on assessment completion, fires `complete` event
    → learningfoundry writes {quizRef, score, maxScore} to its assessment_scores table
    → progress dashboard reads assessment_scores for module-level display
```

---

## Package Distribution

| Concern | Value |
|---------|-------|
| **Python package** | `quizazz` on PyPI |
| **SvelteKit component** | `@pointmatic/quizazz` on npm |
| **learningfoundry dependency** | Optional: `pip install learningfoundry[quizazz]` installs `quizazz` |

---

## Versioning and Compatibility

- learningfoundry pins `quizazz>=0.1` as an optional dependency.
- The manifest dict schema is the versioning boundary. Breaking changes to the manifest structure require a major version bump in `quizazz` and a corresponding update in learningfoundry's `QuizazzProvider`.
- The SvelteKit component and the Python builder must agree on the manifest schema. learningfoundry does not interpret the manifest contents — it passes the dict through opaquely.

---

## Testing Contract

| Test | Owner | What is tested |
|------|-------|----------------|
| `compile_assessment` returns valid manifest for well-formed YAML | quizazz | Unit test in quizazz repo |
| `compile_assessment` raises `ValidationError` for malformed YAML | quizazz | Unit test in quizazz repo |
| `compile_assessment` raises `ValidationError` for `yaml_path` escaping `base_dir` | quizazz | Unit test in quizazz repo |
| learningfoundry's `QuizazzProvider` delegates correctly to `compile_assessment` | learningfoundry | Unit test with mocked `quizazz` |
| learningfoundry's `QuizazzProvider` relabels `quizName` → `assessmentName` (RR-1a) | learningfoundry | Unit test |
| learningfoundry wraps `ValidationError` in `IntegrationError` with block location | learningfoundry | Unit test |
| `QuizBlock` component renders manifest and fires `complete` event | quizazz | Component test in quizazz repo |
| learningfoundry's `QuizBlock` integration writes score to `assessment_scores` table | learningfoundry | Integration test |
