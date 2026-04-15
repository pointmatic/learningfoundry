# dependency-spec.md — d3foundry (as consumed by learningfoundry)

This document defines what learningfoundry **requires** from d3foundry — the contract between the two projects. d3foundry does not yet exist as a library; this spec defines the interface that learningfoundry codes against, enabling a stub implementation for v1 and a real integration when d3foundry is available.

---

## Role in learningfoundry

d3foundry is the **visualization content provider**. It produces interactive or static visualizations that are embedded inline within curriculum lessons — data plots, neural network architecture diagrams, training dynamics visualizations, and interactive data explorers. Visualizations appear at the point in the lesson where the relevant concept is taught, not in a separate tool.

### Integration Points

| learningfoundry Stage | d3foundry Role |
|----------------------|----------------|
| **Content resolution** (Python, build time) | Compile visualization definition → renderable artifact |
| **SvelteKit frontend** (TypeScript, runtime) | Render visualization as a JavaScript component |

Visualizations are passive content — there is no learner completion or scoring event. They do not write to the progress database.

---

## Design Decision: Rendering Approach

### Option A: D3.js Interactive Components (Future)

Full interactive D3.js visualizations (zoomable, hoverable, animated) rendered as Svelte components. Could also broker artifacts from projects like [CNN Explainer](https://poloclub.github.io/cnn-explainer/) or [LLM Visualization](https://bbycroft.net/llm).

**Pros:** Rich interactivity, learner can explore data, strong pedagogical value.
**Cons:** Each visualization type requires custom D3/Svelte code, significant development effort per visualization.

### Option B: JavaScript-Rendered Image Component (v1)

For v1, d3foundry produces a **static visualization artifact** — an image (PNG, SVG, or rendered HTML) that a JavaScript component displays. The component is a thin wrapper: it receives the artifact and renders it in the page. This separates concerns — what d3foundry does under the hood (Matplotlib, D3.js, or anything else) is opaque to learningfoundry.

**Pros:** Simple, works today, d3foundry's internals can evolve without changing the integration contract.
**Cons:** No interactivity in v1.

### Decision

**v1: Option B (JS-rendered image component).** d3foundry returns a visualization artifact (image data or embeddable HTML). learningfoundry's `VisualizationBlock` component renders it. The component is a JavaScript component regardless of whether the content is a static image or an interactive D3 app — this keeps the integration point consistent across v1 and future versions.

**Future: Option A.** d3foundry returns a Svelte component bundle (or configuration for a generic D3 renderer) for interactive visualizations. The `VisualizationBlock` component detects the artifact type and renders accordingly.

---

## Build-Time Requirements (Python API)

### BR-1: Visualization Compilation API

d3foundry must expose a Python API that learningfoundry can call during content resolution to compile a visualization definition into a renderable artifact.

**Required interface:**

```python
def compile_visualization(yaml_path: Path, base_dir: Path) -> dict:
    """
    Compile a visualization definition file into a renderable artifact.

    Args:
        yaml_path: Path to the visualization definition YAML (relative to base_dir).
        base_dir: Root directory for resolving relative paths.

    Returns:
        A dict representing the compiled visualization, suitable for JSON
        serialization and consumption by the visualization frontend component.

        v1 (static image):
        {
            "type": "visualization",
            "source": "d3foundry",
            "ref": "<original ref path>",
            "status": "ready",                # "ready" | "stub"
            "title": "CNN Architecture Overview",
            "caption": "A three-layer CNN for CIFAR-10 classification.",
            "render_type": "image",           # "image" | "html" | "svelte_component"
            "content": "<base64-encoded PNG/SVG>",
            "content_type": "image/svg+xml",  # MIME type
            "alt_text": "Diagram showing conv → pool → conv → pool → FC → softmax"
        }

        v1 (embeddable HTML):
        {
            "type": "visualization",
            "source": "d3foundry",
            "ref": "<original ref path>",
            "status": "ready",
            "title": "Training Loss Over Epochs",
            "caption": "Loss decreases steadily over 20 epochs.",
            "render_type": "html",
            "content": "<div id='chart'>...</div><script>...</script>",
            "content_type": "text/html",
            "alt_text": "Line chart showing training loss decreasing from 2.3 to 0.4"
        }

        Future (interactive Svelte component):
        {
            "type": "visualization",
            "source": "d3foundry",
            "ref": "<original ref path>",
            "status": "ready",
            "title": "Interactive Feature Map Explorer",
            "caption": "Click on a layer to see its feature maps.",
            "render_type": "svelte_component",
            "component_id": "feature-map-explorer",
            "props": { "model": "simple-cnn", "layer_count": 3 },
            "alt_text": "Interactive visualization of CNN feature maps"
        }

    Raises:
        d3foundry.VisualizationError: If the definition is invalid.
            Must include file path and human-readable description.
    """
```

**Behavior:**
1. Read the visualization YAML at `base_dir / yaml_path`.
2. Validate required fields (title, at least one content source).
3. Generate or load the visualization content:
   - **v1 with Matplotlib:** Execute a Python script/function that produces a figure, export to SVG/PNG, base64-encode.
   - **v1 with pre-rendered image:** Load an existing image file, base64-encode.
   - **v1 with HTML:** Load or generate an HTML snippet containing inline JS/CSS.
   - **Future with D3/Svelte:** Bundle the component code and configuration.
4. Return the artifact dict.

**Constraints:**
- Synchronous function, importable from the `d3foundry` package.
- The returned dict must be JSON-serializable.
- Image content is base64-encoded to avoid separate file management.
- For Matplotlib-based visualizations, d3foundry handles `matplotlib.use('Agg')` and figure cleanup internally.

### BR-2: Validation-Only API

```python
def validate_visualization(yaml_path: Path, base_dir: Path) -> list[str]:
    """
    Validate a visualization definition file without rendering.

    Returns:
        An empty list if valid, or a list of human-readable error strings.
    """
```

### BR-3: Error Contract

d3foundry errors must be catchable as `d3foundry.VisualizationError` (or similar), carrying:
- **file_path**: The visualization file that failed.
- **message**: Human-readable description.
- **detail**: Optional structured detail.

---

## Visualization Definition Format (YAML Input)

### Static Image (Matplotlib)

```yaml
title: "CIFAR-10 Class Distribution"
caption: "Balanced distribution: 200 images per class in the training subset."
alt_text: "Bar chart showing 200 images per class across all 10 CIFAR-10 categories"

renderer: matplotlib
script: visualizations/class_distribution.py
function: render           # Function name to call; must return a matplotlib Figure
args:
  data_path: data/cifar10_train_subset.csv
  figsize: [8, 4]
```

### Pre-Rendered Image

```yaml
title: "CNN Architecture Overview"
caption: "A three-layer CNN for CIFAR-10 classification."
alt_text: "Diagram showing conv → pool → conv → pool → FC → softmax"

renderer: static
image: visualizations/cnn_architecture.svg
```

### Embeddable HTML (Future D3.js)

```yaml
title: "Interactive Loss Landscape"
caption: "Hover to explore the loss surface."
alt_text: "3D surface plot of the loss landscape"

renderer: d3
template: visualizations/loss_landscape.html
data: visualizations/loss_landscape_data.json
```

---

## Curriculum YAML Integration

d3foundry visualizations are referenced as a new content block type in the curriculum YAML:

```yaml
content_blocks:
  - type: text
    ref: content/mod-06/lesson-01.md

  - type: visualization
    source: d3foundry
    ref: visualizations/mod-06-cnn-architecture.yml

  - type: text
    ref: content/mod-06/lesson-01-continued.md
```

> **Note:** The `visualization` content block type is not yet in learningfoundry's v1 schema. It will be added when d3foundry integration is implemented. For v1, visualizations are embedded directly in markdown content files as inline images.

---

## Runtime Requirements (SvelteKit Component)

### RR-1: Visualization Display Component

learningfoundry's SvelteKit template includes a `VisualizationBlock` component that renders the compiled artifact.

```svelte
<VisualizationBlock visualization={vizData} />
```

**Props:**
- `visualization` — The compiled visualization dict.

**Rendering behavior by `render_type`:**

| `render_type` | Rendering |
|---------------|-----------|
| `"image"` | `<figure>` with `<img src="data:{content_type};base64,{content}" alt="{alt_text}">`, `<figcaption>` with title and caption |
| `"html"` | `<figure>` with sandboxed `<iframe srcdoc="{content}">`, `<figcaption>` with title and caption |
| `"svelte_component"` | Dynamic Svelte component import by `component_id` with `props` (future) |

**Constraints:**
- HTML content is rendered in a sandboxed iframe to prevent style/script leakage into the main app.
- Images are rendered as standard `<img>` tags with proper `alt` text for accessibility.
- No progress tracking — visualizations are passive content.

---

## Data Flow Summary

```
Build time (Python):
  curriculum.yml
    → content resolution encounters `type: visualization, source: d3foundry, ref: ...`
    → learningfoundry calls d3foundry.compile_visualization(ref, base_dir)
        → d3foundry runs Matplotlib script, loads image, or bundles HTML
    → receives visualization dict (with base64 image or HTML content)
    → serializes to JSON in generated SvelteKit project

Runtime (SvelteKit):
  LessonView renders VisualizationBlock component with visualization data
    → renders <img> (for images) or sandboxed <iframe> (for HTML)
    → no progress tracking, no events
```

---

## Package Distribution

| Concern | Value |
|---------|-------|
| **Python package** | `d3foundry` on PyPI (not yet published) |
| **learningfoundry dependency** | Optional: `pip install learningfoundry[d3foundry]` (future) |
| **v1 stub** | `D3foundryStub` class in `learningfoundry.integrations.d3foundry_stub` returns placeholder visualization dicts |

---

## v1 Stub Behavior

Until d3foundry is published, learningfoundry ships a `D3foundryStub` that implements the `VisualizationProvider` protocol:

```python
class D3foundryStub:
    def compile_visualization(self, ref_path: Path, base_dir: Path) -> dict:
        return {
            "type": "visualization",
            "source": "d3foundry",
            "ref": str(ref_path),
            "status": "stub",
            "title": f"Visualization: {ref_path.stem}",
            "caption": "",
            "render_type": "image",
            "content": "",           # Empty — component renders placeholder
            "content_type": "image/svg+xml",
            "alt_text": f"Placeholder for {ref_path}",
        }
```

The `VisualizationBlock` component detects `status: "stub"` and renders a placeholder card.

---

## v1 Workaround: Inline Markdown Images

Until the `visualization` content block type is added to learningfoundry's schema, authors embed visualizations directly in markdown content files:

```markdown
## CNN Architecture

The model uses three convolutional layers followed by two fully connected layers.

![CNN Architecture](../visualizations/cnn_architecture.svg)

Each convolutional layer applies a 3×3 filter with ReLU activation...
```

learningfoundry's markdown resolver copies referenced images to the generated SvelteKit project's `static/` directory and rewrites the paths. This works for static images only — interactive visualizations require the `visualization` block type.

---

## Versioning and Compatibility

- The visualization dict schema is the versioning boundary.
- The `render_type` field is the extension point: new render types can be added without breaking existing ones.
- The `status` field distinguishes stub content from real content.

---

## Testing Contract

| Test | Owner | What is tested |
|------|-------|----------------|
| `compile_visualization` returns valid artifact for Matplotlib-based YAML | d3foundry | Unit test in d3foundry repo (future) |
| `compile_visualization` returns valid artifact for pre-rendered image YAML | d3foundry | Unit test in d3foundry repo (future) |
| `compile_visualization` raises `VisualizationError` for malformed YAML | d3foundry | Unit test in d3foundry repo (future) |
| learningfoundry's `D3foundryStub` returns correct placeholder structure | learningfoundry | Unit test |
| `VisualizationBlock` renders image artifact as `<img>` with alt text | learningfoundry | Component test |
| `VisualizationBlock` renders HTML artifact in sandboxed iframe | learningfoundry | Component test (future) |
| `VisualizationBlock` renders stub content with placeholder message | learningfoundry | Component test |
| Markdown images are resolved and copied to static directory | learningfoundry | Integration test (v1 workaround) |
