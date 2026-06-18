# Subphase K-1 Plan — NbFoundry Integration

Planning artifact for the **NbFoundry integration** stories under Subphase K-1 of Phase K (pre-1.0; package at v0.79.3). Drafted via `plan_phase` in its "draft a subphase's story bundle" shape — this does **not** open a new phase. Story letters continue monotonically from the existing K-1 tail (`K.c [Done]`), so the integration bundle is **K.d → K.f**.

Grounding contract: [nbfoundry/consumer-dependency-spec.md](nbfoundry/consumer-dependency-spec.md). This plan implements the LearningFoundry side of that contract for the **v1 "Option B" static-exercise** path; the Marimo WASM embed ("Option A") is explicitly out of scope (below).

---

## Distribution model (context that shapes the renderer)

The entire curriculum is **one git repository** — the LearningFoundry-consuming app, the toolchain it pulls in (quizazz, nbfoundry, DataRefinery, modelfoundry), and every authored artifact (markdown, assessment YAML, exercise YAML, notebooks). Initial distribution is `git clone`; an application bundle is deferred.

Consequences:
- Exercises are authored **in-repo** and located by the existing relative `ref` (resolved against `base_dir`). The author organizes content however they like — LearningFoundry imposes **no** source-directory convention.
- The learner already *has* the repo, so there is **no clone-URL / repo field** to add to the curriculum schema. The runnable notebook lives at an author-chosen relative path the learner can open locally.
- The learningfoundry **package** (`src/learningfoundry/`) doesn't import DataRefinery/modelfoundry/nbfoundry directly — it reaches nbfoundry only through the `ExerciseProvider` optional extra (the existing `project-essentials.md` "modelfoundry is NOT a direct dependency" note, which is a *package*-level boundary). A curriculum **application repo** built on learningfoundry *may* import DataRefinery/modelfoundry/nbfoundry directly (for notebooks or app code) — that's the app's choice, outside the package boundary. Either way the toolchain rides along in the clone for the learner's local runs.

---

## Gap analysis — what exists vs. what's needed

**Exists today:**
- `NbfoundryStub.compile_exercise()` returns a `status: "stub"` placeholder dict ([integrations/nbfoundry_stub.py](../../src/learningfoundry/integrations/nbfoundry_stub.py)).
- `ExerciseProvider` protocol: `compile_exercise(ref_path, base_dir) -> dict` ([integrations/protocols.py](../../src/learningfoundry/integrations/protocols.py)).
- Resolver defaults the exercise provider to `NbfoundryStub` ([resolver.py:129-132](../../src/learningfoundry/resolver.py#L129)) and stores the returned dict on the resolved block ([resolver.py:339-343](../../src/learningfoundry/resolver.py#L339)) — but does **not** aggregate any exercise assets.
- `ExerciseBlock.svelte` renders a placeholder for `status: "stub"` and, for the `ready` branch, only **instructions + hints** — no sections, no expected_outputs, no completion event.
- `ExerciseContent` TS interface is loosely typed (`sections: unknown[]`, no `assets`).
- `exercise_status` SQLite table already exists for completion tracking.
- Asset staging exists **only for text-block images** (content-hashed under `static/content/<hash12>/…`, [generator.py:238](../../src/learningfoundry/generator.py#L238)).

**Needed:**
- A real `NbfoundryProvider` delegating to `nbfoundry.compile_exercise`, behind the optional `nbfoundry` extra.
- Per-block `status: stub|ready` on the `ExerciseBlock` as the **single switch** (no new vocabulary — reuses the existing `status` value space), handled in the resolver: `stub` emits a placeholder, `ready` compiles via the one `NbfoundryProvider`. No two-provider fork.
- An explicit exercise `id` for asset-namespacing and progress keying.
- An asset-staging pipeline step: copy the compiled dict's `assets[]` from `base_dir/<path>` → `output_dir/static/exercises/<id>/<path>`.
- A complete `ready`-state `ExerciseBlock` renderer (manual-completion flavor) + real `ExerciseContent` types.

---

## Feature requirements (mini-features)

1. **Real exercise compilation.** When an `exercise` block declares `status: ready` (default), the pipeline compiles it through nbfoundry and the frontend renders the full artifact. When it declares `status: stub`, the build uses the placeholder — no nbfoundry import required.
2. **Incremental authoring.** An author scaffolds a curriculum with `status: stub` exercises and flips them to `ready` one at a time as notebooks get built. Flipping is a one-word YAML edit; a `ready` block with a bad `ref` fails loud (fail-fast / OR-1), never silently degrading to a placeholder.
3. **Rendered exercise.** A `ready` exercise renders its instructions, code `sections` (read-only scaffolding), `expected_outputs` (text/table inline; images via staged URLs with `alt` + lazy loading), and `hints`, then offers a **"Mark as Complete"** control that records completion in `exercise_status`.
4. **Asset fidelity.** Every binary asset an exercise references (e.g. an expected-output image) is staged into the static output and served by the SvelteKit adapter, addressed by a stable per-exercise URL.

---

## Technical changes (mini-tech-spec)

- **`integrations/nbfoundry.py` — `NbfoundryProvider`** (mirror `QuizazzProvider`): `compile_exercise(ref_path, base_dir)` kept signature-identical to the `ExerciseProvider` protocol / nbfoundry's API (**no `status` param** — `status` is resolved upstream, not inside the provider, so the protocol-match contract test holds). Lazy `from nbfoundry import compile_exercise`; `ImportError` with a `pip install learningfoundry[nbfoundry]` hint; wrap any nbfoundry exception in `IntegrationError` citing `ref_path`. `NbfoundryStub` is **demoted to a test double / injectable** — not the default, not status-routed.
- **`pyproject.toml`** — add the `[project.optional-dependencies].nbfoundry = ["nbfoundry>=<released-floor>"]` extra (currently only `quizazz` is present).
- **`schema_v1.py` `ExerciseBlock`** — add `status: Literal["stub", "ready"] = "ready"` and `id: str | None = None` (auto-derived from the `ref` stem when omitted; intra-curriculum uniqueness enforced at parse time, mirroring the `AssessmentDefinition.id` precedent from Story J.r). The `id` namespaces *build output*, not author source.
- **`resolver.py`** — handle `block.status` in one place: `"stub"` → emit the placeholder via a shared `stub_exercise(ref)` factory (no provider call, no nbfoundry import); `"ready"` (default) → the one injected `NbfoundryProvider`. For each compiled exercise, read the dict's `assets: list[str]` and emit `Asset(source=base_dir/path, dest_relative="exercises/<id>/<path>")` into the existing `assets_by_dest` aggregator.
- **`generator.py`** — the existing asset-copy loop already writes any `dest_relative`; add `"static/exercises"` to `_PRESERVED_PATHS` ([generator.py:40](../../src/learningfoundry/generator.py#L40)) alongside `static/content`.
- **`ExerciseBlock.svelte`** — build out the `ready` branch: `sections` (code blocks; the `editable` flag is cosmetic in v1, reserved for the WASM future), `expected_outputs` (image via runtime-composed `/exercises/${id}/${path}` + `loading="lazy"` + `alt`), "Mark as Complete" → fire the `complete` event `{exerciseRef: id, status: "completed"}` → `exercise_status` write.
- **`lib/types/index.ts` `ExerciseContent`** — replace the `unknown[]` placeholders with real `sections` / `expected_outputs` / `assets` shapes. This is the **Python-dict ↔ TS-interface Hidden Coupling** — the input Pydantic enum, the compiled dict, and the TS type must agree.
- **Contract test** — assert `NbfoundryProvider` satisfies the `ExerciseProvider` protocol (the consumer-dependency-spec testing-matrix item), keeping `protocols.py` ↔ `consumer-dependency-spec.md` in sync.

---

## Story breakdown (preview — added to `stories.md` in Step 6 after this plan is approved)

- **K.d — `NbfoundryProvider` + `nbfoundry` extra + `status` handling.** Python-only. Provider, optional extra, `ExerciseBlock.status` schema; the resolver short-circuits `stub` to a placeholder factory and compiles `ready` via the one provider (no two-provider fork; stub demoted to test double). Contract/type-check test. Shippable alone (existing thin `ready` renderer still draws instructions+hints).
- **K.e — Exercise `id` + asset staging.** `id` schema (auto-derived + unique), resolver emits `Asset` records → `static/exercises/<id>/<path>`, `_PRESERVED_PATHS += static/exercises`, generator/asset tests.
- **K.f — `ExerciseBlock` ready renderer (manual-completion).** Sections + expected_outputs (incl. staged images) + "Mark as Complete" → `exercise_status`; real `ExerciseContent` TS types; vitest coverage. Pins the learner's local-run affordance (see open item below).

An **integration spike** is *not* proposed: the boundary contract (`consumer-dependency-spec.md`) is already specified and stable, and K.d's contract test is the verification. If nbfoundry's released `compile_exercise` diverges from the spec on first real call, K.d converts to a spike at that point.

---

## Out of scope (negotiated → deferred to `## Future`)

- **Graded submission** — the optional `submission` block (typed input fields + the locked range/equals/contains_all scoring formula + score storage). Confirmed deferred; the manual-completion path ships value without it, and `submission` is forward-compatible (no YAML rewrite when it lands).
- **Marimo WASM embed ("Option A")** — in-browser notebook execution. Deferred; the v1 contract is forward-designed to accommodate it without re-authoring exercises.
- **Downloadable application bundle** — v1 distribution is `git clone` of the curriculum repo.
- **d3foundry / `VisualizationProvider`** — separate integration, not part of K-1.
- **DataRefinery / modelfoundry direct integration *by the learningfoundry package*** — the package reaches them only inside nbfoundry. (A curriculum *application* repo may import them directly; that's an app-layer choice, not a package one — see the Distribution-model note above.)

---

## Open item to pin during K.f

**How (if at all) the renderer points the learner at the runnable notebook.** Since the author organizes content freely and the learner has the whole repo, the renderer surfaces whatever the compiled dict provides. If `compile_exercise`'s dict carries a notebook-location field, K.f surfaces it ("open `<relative-path>` and run locally"); if not, the learner relies on the rendered `sections` plus their cloned repo. This is an nbfoundry-contract / authoring-convention detail to confirm against the released package during K.f — not a blocker for K.d/K.e.
