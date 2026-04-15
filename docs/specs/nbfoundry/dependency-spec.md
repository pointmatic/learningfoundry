# dependency-spec.md — nbfoundry (as consumed by learningfoundry)

This document defines what learningfoundry **requires** from nbfoundry — the contract between the two projects. nbfoundry does not yet exist as a library; this spec defines the interface that learningfoundry codes against, enabling a stub implementation for v1 and a real integration when nbfoundry is available.

---

## Role in learningfoundry

nbfoundry is the **experiential content provider**. It produces interactive, executable notebook-based exercises that learners complete within the curriculum. In the D802 Deep Learning Essentials curriculum, these exercises involve building neural networks, training models, and analyzing results — with nbfoundry handling the scaffolding (data loading, training loops, evaluation) and providing explicit insertion points where the learner writes code.

nbfoundry depends on **modelfoundry** internally for data preparation, model training, optimization, and evaluation scaffolding. learningfoundry does not interact with modelfoundry directly — it is an implementation detail of nbfoundry.

### Integration Points

| learningfoundry Stage | nbfoundry Role |
|----------------------|----------------|
| **Content resolution** (Python, build time) | Compile exercise definition → renderable exercise artifact |
| **SvelteKit frontend** (TypeScript, runtime) | Render interactive exercise in the browser |
| **Progress tracking** (runtime) | Report exercise completion event to learningfoundry's progress database |

---

## Design Decision: Rendering Approach

nbfoundry exercises need to render executable Python code in the browser. Two approaches are viable:

### Option A: Marimo WASM Embed (Recommended for future)

[Marimo](https://marimo.io) supports [WASM-based browser execution](https://docs.marimo.io/guides/wasm/) — a full Python runtime (via Pyodide) running in the browser with reactive notebook semantics. This would allow learners to write and execute Python code directly within the learningfoundry SvelteKit app with no server.

**Pros:** True in-browser code execution, reactive cells, rich output (plots, tables), no server infrastructure.
**Cons:** Large WASM payload (~40MB Pyodide), cold start latency, limited library support in Pyodide (PyTorch not available in WASM), complexity of embedding.

### Option B: Static Exercise Display (v1)

For v1, nbfoundry produces a **static exercise artifact** — structured content (instructions, code scaffolding, expected outputs) that learningfoundry renders as read-only content blocks. The learner reads the exercise, works in a separate local environment (JupyterLab, Marimo desktop, VS Code), and marks the exercise as complete in the app.

**Pros:** Simple, no WASM complexity, works with any Python library (including PyTorch/GPU).
**Cons:** Breaks the unified experience — learner must context-switch to a separate environment.

### Decision

**v1: Option B (static exercise display).** The exercises are blackbox content — nbfoundry returns structured data, learningfoundry renders it, no data handoff or code execution in the browser. The exercise content is curated by the author, not auto-generated.

**Future: Option A (Marimo WASM embed)** for exercises that don't require GPU-dependent libraries. The interface is designed to accommodate both approaches — the `ExerciseProvider` protocol returns a dict that can represent either static content or a Marimo WASM bundle.

---

## Build-Time Requirements (Python API)

### BR-1: Exercise Compilation API

nbfoundry must expose a Python API that learningfoundry can call during content resolution to compile a single exercise definition file into a renderable artifact.

**Required interface:**

```python
def compile_exercise(yaml_path: Path, base_dir: Path) -> dict:
    """
    Compile an exercise definition file into a renderable exercise artifact.

    Args:
        yaml_path: Path to the exercise definition YAML file (relative to base_dir).
        base_dir: Root directory for resolving relative paths within the YAML.

    Returns:
        A dict representing the compiled exercise, suitable for JSON serialization
        and consumption by the exercise frontend component. Structure:

        {
            "type": "exercise",
            "source": "nbfoundry",
            "ref": "<original ref path>",
            "status": "ready",           # "ready" | "stub"
            "title": "Build a CNN Classifier",
            "instructions": "<HTML string>",    # Rendered from markdown
            "sections": [
                {
                    "title": "Data Loading",
                    "description": "<HTML>",
                    "code": "import torch\\n...",     # Pre-filled code
                    "editable": false                  # Scaffold (read-only)
                },
                {
                    "title": "Define Your Model",
                    "description": "<HTML>",
                    "code": "# YOUR CODE HERE\\n...", # Insertion point
                    "editable": true                   # Learner writes here
                },
                {
                    "title": "Training Loop",
                    "description": "<HTML>",
                    "code": "for epoch in range(...)...",
                    "editable": false
                },
                {
                    "title": "Evaluate Results",
                    "description": "<HTML>",
                    "code": "",
                    "editable": true
                }
            ],
            "expected_outputs": [
                {
                    "description": "Training loss curve",
                    "type": "image",               # "image" | "text" | "table"
                    "content": "<base64 PNG or placeholder>"
                }
            ],
            "hints": [
                "Start with nn.Conv2d for the first layer.",
                "Remember to flatten before the fully connected layer."
            ],
            "environment": {
                "python_version": "3.12",
                "dependencies": ["torch", "torchvision", "matplotlib"],
                "setup_instructions": "Run `pip install -r requirements.txt` in your local environment."
            }
        }

    Raises:
        nbfoundry.ExerciseError: If the exercise definition is invalid.
            Must include file path and human-readable description.
    """
```

**Behavior:**
1. Read the exercise YAML at `base_dir / yaml_path`.
2. Validate required fields (title, instructions, at least one section).
3. Render markdown fields to HTML.
4. Resolve any referenced code files or data files.
5. Return the compiled exercise dict.

**Constraints:**
- Synchronous function, importable from the `nbfoundry` package.
- No side effects beyond reading referenced files.
- The returned dict must be JSON-serializable.

### BR-2: Exercise Validation API

```python
def validate_exercise(yaml_path: Path, base_dir: Path) -> list[str]:
    """
    Validate an exercise definition file without compiling.

    Returns:
        An empty list if valid, or a list of human-readable error strings.
    """
```

### BR-3: Error Contract

nbfoundry errors must be catchable as `nbfoundry.ExerciseError` (or similar), carrying:
- **file_path**: The exercise file that failed.
- **message**: Human-readable description.
- **detail**: Optional structured detail (section index, field name).

---

## Exercise Definition Format (YAML Input)

The curriculum author writes exercise definitions in YAML. This is the input format that nbfoundry consumes:

```yaml
title: "Build a CNN Classifier"
description: |
  In this exercise, you'll build a convolutional neural network to classify
  CIFAR-10 images. The data loading and training loop are provided — your
  job is to define the model architecture and evaluation logic.

sections:
  - title: "Data Loading"
    description: "Pre-built data pipeline. Review but do not modify."
    code_file: scaffolds/data_loading.py
    editable: false

  - title: "Define Your Model"
    description: |
      Build a CNN with at least two convolutional layers. Use `nn.Conv2d`,
      `nn.ReLU`, `nn.MaxPool2d`, and `nn.Linear`.
    code: |
      import torch.nn as nn

      class SimpleCNN(nn.Module):
          def __init__(self):
              super().__init__()
              # YOUR CODE HERE: define layers

          def forward(self, x):
              # YOUR CODE HERE: define forward pass
              pass
    editable: true

  - title: "Training Loop"
    description: "Standard training loop. Review to understand the process."
    code_file: scaffolds/training_loop.py
    editable: false

  - title: "Evaluate Results"
    description: "Compute accuracy on the test set and plot the loss curve."
    code: |
      # YOUR CODE HERE: compute test accuracy
      # YOUR CODE HERE: plot training loss curve
    editable: true

expected_outputs:
  - description: "Training loss should decrease over epochs"
    type: image
    reference: references/expected_loss_curve.png

  - description: "Test accuracy should exceed 65%"
    type: text
    content: "Expected: accuracy >= 0.65"

hints:
  - "Start with nn.Conv2d(3, 16, kernel_size=3, padding=1) for the first layer."
  - "Use nn.MaxPool2d(2) to reduce spatial dimensions."
  - "Remember to flatten the tensor before the fully connected layer."

environment:
  python_version: "3.12"
  dependencies:
    - torch
    - torchvision
    - matplotlib
```

---

## Runtime Requirements (SvelteKit Component)

### RR-1: Exercise Display Component

learningfoundry's SvelteKit template includes an `ExerciseBlock` component that renders the compiled exercise artifact.

**For v1 (static display):**

```svelte
<ExerciseBlock
  exercise={exerciseData}
  exerciseRef={refPath}
  on:complete={handleExerciseComplete}
/>
```

**Props:**
- `exercise` — The compiled exercise dict.
- `exerciseRef` — Unique string identifying this exercise instance (ref path from curriculum YAML).

**Events:**
- `complete` — Fired when the learner manually marks the exercise as complete.

```typescript
interface ExerciseCompleteEvent {
  exerciseRef: string;
  status: "completed";    // v1: only manual completion
}
```

**v1 Rendering Behavior:**
1. Display exercise title and instructions.
2. Render each section with its title, description, and code block (syntax-highlighted).
3. Visually distinguish editable sections (insertion points) from scaffold sections (read-only).
4. Display expected outputs (images, text).
5. Provide collapsible hints.
6. Display environment/setup instructions so the learner knows how to run the exercise locally.
7. Provide a "Mark as Complete" button that fires the `complete` event.

**Future (Marimo WASM) Rendering Behavior:**
- If the exercise dict includes a `marimo_wasm_bundle` field, render an embedded Marimo WASM notebook instead of static code blocks.
- The learner writes and executes code in-browser.
- Completion is detected automatically when expected outputs are produced.

### RR-2: No Data Handoff (v1)

In v1, there is no data transfer between the SvelteKit app and the learner's local Python environment. The exercise is purely informational — it shows what to build and what to expect, but execution happens externally. The `ExerciseBlock` component does not execute code.

---

## Data Flow Summary

```
Build time (Python):
  curriculum.yml
    → content resolution encounters `type: exercise, source: nbfoundry, ref: ...`
    → learningfoundry calls nbfoundry.compile_exercise(ref, base_dir)
        → nbfoundry internally uses modelfoundry for scaffolding (opaque to learningfoundry)
    → receives exercise dict
    → serializes to JSON in generated SvelteKit project

Runtime (SvelteKit):
  LessonView renders ExerciseBlock component with exercise data + exerciseRef
    → v1: static display of instructions, code, expected outputs
    → learner works locally, then clicks "Mark as Complete"
    → fires `complete` event
    → learningfoundry writes {exerciseRef, status: "completed"} to exercise_status table
    → progress dashboard reads exercise_status for module-level display
```

---

## Package Distribution

| Concern | Value |
|---------|-------|
| **Python package** | `nbfoundry` on PyPI (not yet published) |
| **learningfoundry dependency** | Optional: `pip install learningfoundry[nbfoundry]` (future) |
| **v1 stub** | `NbfoundryStub` class in `learningfoundry.integrations.nbfoundry_stub` returns placeholder exercise dicts |

---

## v1 Stub Behavior

Until nbfoundry is published, learningfoundry ships a `NbfoundryStub` that implements the `ExerciseProvider` protocol:

```python
class NbfoundryStub:
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

The `ExerciseBlock` component detects `status: "stub"` and renders a placeholder card with the message.

---

## Versioning and Compatibility

- The exercise dict schema is the versioning boundary. The `status` field distinguishes stub content from real content.
- When nbfoundry is published, learningfoundry adds it as an optional dependency and replaces the stub with a real `NbfoundryProvider` that delegates to `nbfoundry.compile_exercise`.
- The SvelteKit `ExerciseBlock` component handles both stub and real exercise dicts.

---

## Testing Contract

| Test | Owner | What is tested |
|------|-------|----------------|
| `compile_exercise` returns valid artifact for well-formed YAML | nbfoundry | Unit test in nbfoundry repo (future) |
| `compile_exercise` raises `ExerciseError` for malformed YAML | nbfoundry | Unit test in nbfoundry repo (future) |
| learningfoundry's `NbfoundryStub` returns correct placeholder structure | learningfoundry | Unit test |
| learningfoundry's `ExerciseProvider` protocol matches nbfoundry's API | learningfoundry | Type check (mypy) |
| `ExerciseBlock` renders stub content with placeholder message | learningfoundry | Component test |
| `ExerciseBlock` renders real exercise with sections and hints | learningfoundry | Component test (future, with fixture data) |
| `ExerciseBlock` fires `complete` event on "Mark as Complete" click | learningfoundry | Component test |
