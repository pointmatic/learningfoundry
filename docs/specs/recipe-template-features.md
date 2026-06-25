<!--
Copyright (c) 2026 Michael Smith
SPDX-License-Identifier: Apache-2.0
-->

# Recipe Template Features - Request for Templated Recipes in LearningFoundry

**From:** a LearningFoundry consumer
**Ask:** promote the project-local recipe-templating we hand-rolled in
`scripts/render_recipe.py` into a first-class LearningFoundry capability that an
**exercise author declares in the exercise YAML** — a recipe *template* + a set of
*parameters* — and LF renders a concrete recipe that can be handed to **either
DataRefinery or ModelFoundry**.

Companion docs: [`recipe-template-spec.md`](recipe-template-spec.md) (the project-side
convention + migration path) and the reference implementation at
`scripts/render_recipe.py` (+ `scripts/test_render_recipe.py`, + the two worked
templates `models/resnet20.template.yaml` / `models/resnet20_optuna.template.yaml`).

---

## §1 The ask in one paragraph

A recipe (DataRefinery or ModelFoundry) is a precise, interdependent document — the
wrong altitude to hand a learner. The exercise's **pedagogical pinhole** is the
*few* parameters the learner manipulates (a CNN's learning rate, weight decay,
batch size, epochs); everything else is backdrop. We want LF to let an author
declare those few parameters and a recipe template **in the exercise YAML**, and
have LF render a concrete, valid recipe behind the scenes — so the learner edits
parameters, never the recipe. The recipe stays a technical artifact, the way you
edit a Word document through the app rather than hand-tweaking its XML.

---

## §2 What we built (the hand-rolled reference)

`scripts/render_recipe.py` (Story E.d) — **strict deep-merge override**:

- **The template is a complete, valid recipe** with every knob at its default
  value, so `modelfoundry validate <template>` / `datarefinery` accept it as-is
  (no `${...}` placeholder tokens that would break parsing/validation).
- **`render_recipe(template, params)`** deep-merges a *partial* mapping (mirroring
  the recipe's nesting) onto the template and returns a new document. The merge is
  **strict**: an override key absent from the template, or a leaf that changes
  between scalar and mapping, raises `RenderError`. That structurally enforces "you
  may override only knobs the template already declares," so a typo fails loud
  instead of silently injecting a key the tool later rejects.
- Key order follows the template; the rendered file carries a `# GENERATED …`
  provenance header. CLI: `--out`, `--params <file>`, `--set dotted.key=value`.
- Worked templates: `models/resnet20.template.yaml`,
  `models/resnet20_optuna.template.yaml` (their headers list the surfaced knobs).
  12 unit tests in `tests/test_render_recipe.py`.

**Why deep-merge, not placeholder substitution** (carry this rationale into the LF
design): the template stays a real, validatable recipe; it needs only stdlib +
PyYAML; an unknown/misspelled override fails loud; override values keep their
parsed type. The "render with no params" path reproduces the canonical recipe.

**Known limitations of the hand-rolled version** (the LF feature should resolve
these — see §4):
1. **Which keys are surfaced is implicit** — inferred from whatever the params
   mapping happens to touch, not declared. A template can't, by itself, tell a UI
   which values are editable.
2. **No types/ranges** — the merge enforces "key exists" and "scalar↔mapping
   shape," not "LR ∈ (0, 1)."
3. **Coupled params are the caller's problem** — e.g. a cosine schedule's `T_max`
   conventionally equals `Training.max_epochs`; the deep-merge can't express "one
   knob → two recipe paths," so the exercise sets both by hand.
4. **Literal dotted keys** — ModelFoundry's `Optimization.search_space` keys are
   literal dotted strings (`"Optimizer.learning_rate"`); the dotted-`--set` CLI
   can't address them (a `--params` file can).
5. **Template ↔ live-recipe drift** — each `*.template.yaml` mirrors a live recipe
   by hand until this feature collapses them to one source.

---

## §3 The desired LearningFoundry feature

### §3.1 Authoring surface — declared in the exercise YAML

An exercise (or a section) names a template and the surfaced parameters; LF renders
the recipe and exposes it to the notebook for DR/MF to consume:

```yaml
# exercise YAML
recipe:
  template: models/resnet20.template.yaml   # a recipe template (see §3.3)
  parameters:                                # the surfaced knobs (learner-editable)
    learning_rate: 0.001
    weight_decay: 0.0001
    batch_size: 64
    epochs: 40
```

LF renders a concrete recipe from `template` + `parameters` and makes it available
to the notebook (as a path and/or an object). The surfaced `parameters` are also
exposed to the notebook as variables, so the learner edits *those* — the recipe is
never shown.

### §3.2 Output — a recipe for DataRefinery *or* ModelFoundry

The rendered artifact is a plain recipe document in the schema DR/MF already
accept. The feature is **tool-agnostic**: it renders a recipe; it does not care
which tool consumes it. The notebook hands the rendered recipe to
`DataRefinery.from_recipe(...)` or `ModelFoundry.from_recipe(...)` exactly as it
would a hand-written one. (Render-with-defaults should hash-identically to the
equivalent hand-written recipe, so an unchanged template is a cache hit — the
behavior we verified for `resnet20.template.yaml` → the trained instance.)

### §3.3 The template doubles as the parameter schema (typed placeholders)

The centerpiece. Rather than "a complete recipe with defaults" (where the surfaced
set is implicit), let a template declare each surfaced value as a **typed
placeholder**, so the **recipe IS the parameter schema** — one artifact, not a
recipe plus a separate schema file. Sketch (placeholder syntax is an open
question — see §6):

```yaml
# models/resnet20.template.yaml  (typed-placeholder form)
Optimizer:
  op: adamw                                  # fixed (backdrop)
  learning_rate: !param {type: float, default: 0.001, range: [1.0e-5, 1.0e-1], label: "Learning rate"}
  weight_decay:  !param {type: float, default: 1.0e-4, range: [0, 1.0e-2]}
  schedule:
    op: cosine
    T_max: !param {ref: epochs}              # coupled: follows the `epochs` knob (§3.4)
Training:
  max_epochs: !param {name: epochs, type: int, default: 40, label: "Epochs"}
  batch_size: !param {type: int, choices: [48, 64, 96], default: 64, label: "Batch size"}
  device: cpu                                # fixed (backdrop)
```

From a typed-placeholder template LF can:
- **Enumerate the surfaced parameters** (every `!param`) — no implicit inference.
- **Validate** a learner's value against `type` + `range`/`choices`, failing loud
  on a bad value (closes hand-rolled limitation 1–2).
- **Render UI controls** — a float slider over `range`, a dropdown over `choices`,
  a labeled input from `label`.
- **Render a concrete recipe** by substituting validated values for the
  placeholders (every non-`!param` value is fixed backdrop).

This subsumes the deep-merge: the deep-merge had to *infer* the surfaced set from
the params mapping; typed placeholders make it **explicit and self-describing** in
the template.

### §3.4 Coupled / multi-path parameters

A surfaced knob should be bindable to **more than one** recipe path, or to a
derived value (closes hand-rolled limitation 3). In the sketch above, `epochs`
drives both `Training.max_epochs` and `Optimizer.schedule.T_max` via a named
`!param {name: epochs}` + a `!param {ref: epochs}`. The exact mechanism (named refs,
computed expressions) is the LF team's call; the requirement is that one learner
knob can fan out to several recipe locations so coupled settings stay consistent.

### §3.5 Format: YAML now, JSON-capable later

The renderer operates on the **parsed document tree**, so it is format-neutral. The
schema-template, the typed placeholders, and the substitution logic are identical
whether the source is YAML or JSON — only the load/dump adapter differs.
**Implement the YAML renderer now**; keep the core format-neutral so a JSON
template renderer is a thin adapter added later (no design change).

---

## §4 Functional requirements (for the LF team)

- **FR-1 — Declarative authoring.** An exercise YAML may declare `recipe.template`
  + `recipe.parameters`; LF renders a concrete recipe from them.
- **FR-2 — Valid output for DR *and* MF.** The rendered recipe is accepted by
  `DataRefinery.from_recipe` and `ModelFoundry.from_recipe` unchanged; tool-agnostic.
- **FR-3 — Strict surfacing.** Only declared/surfaced parameters may be set; an
  unknown key or a type/range violation fails loud (no silent injection).
- **FR-4 — Template-as-schema.** A template may declare values as **typed
  placeholders** (`type`, `default`, `range`/`choices`, `label`), so the recipe
  doubles as the parameter schema; non-placeholder values are fixed.
- **FR-5 — Validation.** Learner values are validated against the declared type and
  range/choices before rendering.
- **FR-6 — Coupled params.** A single surfaced knob may bind to multiple recipe
  paths (or a derived value).
- **FR-7 — Notebook exposure.** Surfaced parameters are exposed to the notebook as
  editable variables; the rendered recipe is exposed as a path/object.
- **FR-8 — Render-with-defaults fidelity.** Rendering with default parameters
  produces a recipe equivalent to the hand-written one (cache-hit identical for
  MF/DR instance hashing).
- **FR-9 — Format-neutral core.** YAML implemented now; the core tree-substitution
  logic is format-agnostic so a JSON renderer is a later adapter.

---

## §5 Migration path (retire the project-local script)

(consumer-specific implementation details omitted)

---

## §6 Open questions

1. **Placeholder syntax.** YAML tags (`!param { … }`) are clean but need a custom
   loader and don't carry into JSON; a reserved mapping key
   (`{ __param__: { … } }`) is loader-agnostic and JSON-portable but noisier. A
   sidecar schema keeps the recipe a plain document but reintroduces the two-file
   drift this feature exists to remove. Recommendation: a reserved-key form, for
   the YAML/JSON portability FR-9 wants.
2. **Validate-as-is vs. render-first.** The hand-rolled deep-merge template
   validates as a recipe as-is (no placeholders). A typed-placeholder template does
   **not** (the tool would see `!param`/`__param__`), so it must be
   rendered-with-defaults before `validate`. Decide whether LF validates the
   *rendered* recipe (likely) or teaches DR/MF to tolerate placeholders.
3. **Rendered-recipe lifetime.** In-memory object handed to DR/MF, or a temp file?
   DR/MF currently take a path or cache-root; an object surface (`from_rendered(...)`)
   would avoid temp files.
4. **Range/choice provenance for the report.** The surfaced ranges are also quoted
   in submission prose (e.g. the Optuna search space). A machine-readable schema
   lets the report cite them without drift — worth exposing.
