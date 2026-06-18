# stories.md -- learningfoundry (python)

This document breaks the `learningfoundry` project into an ordered sequence of small, independently completable stories grouped into phases. Each story has a checklist of concrete tasks. Stories are organized by phase and reference modules defined in `tech-spec.md`.

Put **`vX.Y.Z` in the story title only when that story ships the package version bump** for that release. Doc-only or polish stories **omit the version from the title** (they share the release with the preceding code story, or use your project’s doc-release policy). **One semver bump per owning story** — extra tasks on the *same* story share that bump; see `project-essentials.md`. Semantic versioning applies to the package. Stories are marked with `[Planned]` initially and changed to `[Done]` when completed.

For a high-level concept (why), see [`concept.md`](concept.md). For requirements and behavior (what), see [`features.md`](features.md). For implementation details (how), see [`tech-spec.md`](tech-spec.md). For project-specific must-know facts, see [`project-essentials.md`](project-essentials.md) (`plan_phase` appends new facts per phase). For the workflow steps tailored to the current mode (cycle steps, approval gates, conventions), see [`docs/project-guide/go.md`](../project-guide/go.md) — re-read it whenever the mode changes or after context compaction.

---

## Version Cadence

Standard semantic versioning, with these conventions:

- **Every story belongs to a phase.** Bugfix stories included. No orphan stories.
- **Per-story bumping** (when a story owns its own release):
  - Bugfix or trivial change → **patch** (`vX.Y.Z+1`)
  - Feature or improvement → **minor** (`vX.Y+1.0`)
  - Breaking change → **major** (`vX+1.0.0`). Post-1.0 only, and only via the `plan_production_phase` mode, which negotiates with the developer about whether the breakage is substantively user-facing or technically-but-trivially breaking (example: a log-format change is technically breaking, but if logs aren't a core consumer capability, the developer may judge it minor or even patch).
- **Phase-bundling option:** a phase can run unversioned during work and ship a single release/tag at end-of-phase. Stories within the phase carry no version in their title; the phase's last story owns the bump (magnitude determined by the highest-impact change in the bundle).
- **No out-of-order implementation.** Story order in this file is the order of execution. If work order needs to change, **reorganize/renumber here first** — don't skip ahead and create version-number gaps.
- **Pre-1.0:** standard semver applies; version starts at `v0.1.0` (Story A.a).
- **Post-1.0:** every phase must go through `plan_production_phase` (the lighter `plan_phase` is pre-1.0 only). Major bumps only happen through that mode's negotiation step.

This is the authoritative cadence rule. **Do not extrapolate the bump magnitude from `pyproject.toml`'s current version** — re-read this section whenever you're about to assign a version to a story.

---

## Phase K: 

In this phase we will complete unfinished work from previous phases and fix bugs while working through example use cases to validate the system. 

---

## Subphase K-1: NbFoundry Integration, and Bug Fixes

- **nbfoundry real integration** — Replace `NbfoundryStub` with Marimo notebook generation when nbfoundry is published
- **Cross-tab anti-clobber for the same `userId`.** Two tabs of the same browser, same user, can still last-writer-wins on the IDB blob — Web Locks `+` reload-on-write or BroadcastChannel-based leader election would solve it. Latent issue, distinct from this story; revisit when there's evidence of multi-tab learner workflows or sync work makes it forced. (Same scoping note as I.v.)

### Story K.a: v0.79.3 — `learningfoundry preview` Hangs Silently on `pnpm install`, Then Reports an Empty Failure [Done]

Debug-cycle story. Running `learningfoundry preview` against a `dist/` that needs dependencies printed `Installing Node dependencies in dist` and then produced no further output — an apparent silent hang. On Ctrl-C it reported `` Generation error: `pnpm install` failed in `dist`: `` with nothing after the colon.

**Root cause:** [pipeline.py](../../src/learningfoundry/pipeline.py) ran the install step as `subprocess.run(["pnpm", "install"], cwd=output_dir, capture_output=True, text=True)` (no timeout). Capturing the output had two consequences: (1) pnpm's progress and any *interactive prompt* (pnpm 10 build-script approval, store/lock waits, registry auth) were piped away from the terminal while stdin stayed attached — so a prompting or slow install presented as a silent hang with no way to see why; (2) the non-zero-exit branch interpolated only `result.stderr` into the `GenerationError`. When the process is killed by Ctrl-C (or when pnpm writes its diagnostics to stdout rather than stderr), `result.stderr` is empty, yielding the dead-end `` failed in `dist`: `` message. The sibling `pnpm run dev` call in the same function already streamed to the terminal; the install call was the inconsistent one.

**Why tests didn't catch it.** The existing `run_preview` tests (`TestRunPreviewSkipsInstall`) mock `subprocess.run` and assert *which* commands run for each `DepState`, but never assert *how* the install streams, nor exercise the non-zero-exit failure branch. The capture flag and the empty-stderr message were structurally invisible to the suite.

**Fix:** drop `capture_output=True, text=True` from the install call so pnpm inherits the terminal (progress + prompts visible), matching `pnpm run dev`; and rewrite the failure message to name the exit code and point at the now-visible output instead of interpolating a possibly-empty captured stderr.

**Tasks:**

- [x] `src/learningfoundry/pipeline.py`: remove `capture_output=True, text=True` from the `pnpm install` `subprocess.run(...)`; add a comment explaining why the install must stream. Rewrite the `returncode != 0` `GenerationError` to `` `pnpm install` failed in `<dir>` (exit code N); see the pnpm output above.``
- [x] `tests/test_pipeline.py`: add `TestRunPreviewInstallVisibility` with two regression tests — (a) the install call does not pass `capture_output=True`; (b) a non-zero install with empty stderr raises a `GenerationError` whose message doesn't dead-end at an empty colon and surfaces the exit code. Both fail pre-fix (test (b) reproduces the exact `` failed in `dist`: `` message); both pass post-fix.
- [x] Prevention scan — other captured/long-running subprocess calls: `grep -rn 'subprocess.run\|capture_output' src/learningfoundry/` returns only the two pipeline calls (install now streams; `pnpm run dev` already streamed). No other instance of the anti-pattern in our code; the only other hits are vendored under `node_modules/`.
- [x] Full suite green: `pyve test` → 413 passed, no regressions.
- [x] No `features.md` / `tech-spec.md` change — the bug was implementation-level (subprocess wiring), no requirements ambiguity, no public-API surface change.
- [ ] **Follow-up — friendly Ctrl-C handling in the `preview` CLI command.** Streaming surfaces *why* an install is stuck, but a genuinely wedged install still needs a manual Ctrl-C, which now propagates a `KeyboardInterrupt` through the CLI. A future story could catch it in [cli.py](../../src/learningfoundry/cli.py)'s `preview` for a clean `Interrupted.` message. A bounded install `timeout` was considered and **rejected**: it risks killing valid cold-cache installs. Its own story.
- [x] `CHANGELOG.md`: v0.79.3 (summary of fixes).
- [x] Bump version to v0.79.3 in `pyproject.toml` and `src/learningfoundry/__init__.py`. The `sveltekit_template/package.json` remains pinned at `0.0.1` (template, not a published package).

### Story K.b: Fix stale `tech-spec.md` "WASM Binary Handling" doc [Done]

Doc-accuracy fix, surfaced during Story K.a's spec-review pass. [tech-spec.md](tech-spec.md)'s "WASM Binary Handling" section still described the pre-Story-I.cc mechanism — wasm "copied … during `pnpm install` via a postinstall script" — and an outdated `locateFile` form. Both had drifted from the implemented code: the postinstall hook was replaced by `pipeline._ensure_sql_wasm` (runs every preview/build regardless of `DepState`; raises `GenerationError` if the source is missing), and the frontend uses `locateFile: () => '/sql-wasm.wasm'` ([database.ts:204](../../src/learningfoundry/sveltekit_template/src/lib/db/database.ts#L204)), not `(file) => \`/${file}\``. No version bump (doc-only; rides the next code release).

**Tasks:**

- [x] `docs/specs/tech-spec.md` "WASM Binary Handling": replace the postinstall-script description with the `_ensure_sql_wasm` mechanism (every-build provisioning, content-stale size check, `GenerationError` on missing source, Story I.cc replacement note) and correct the `locateFile` form to `() => '/sql-wasm.wasm'`.
- [x] Cross-checked against [pipeline.py `_ensure_sql_wasm`](../../src/learningfoundry/pipeline.py), [database.ts](../../src/learningfoundry/sveltekit_template/src/lib/db/database.ts), and the `project-essentials.md` "single owner of the asset" note — all three now agree.
- [x] No code/test change — documentation only.

### Story K.c: Promote sql.js robustness-patterns doc to active; archive the bug post-mortem [Done]

Doc-curation follow-up to K.b's link-rot finding. Two sql.js docs had inverted lifecycles: `bug-sql-js-browser-esm-spec.md` (a *resolved* single-bug post-mortem, fully superseded by Story J.y + CHANGELOG) sat active in `docs/specs/`, while `sql-js-wasm-robustness.md` (the reusable patterns reference, linked from the Future item and `project-essentials.md`) had been renamed and archived — leaving its live links broken and its own relative links off by one directory level. The reusable reference is the one worth keeping active; the post-mortem belongs in the archive. The developer performed the file moves (un-archive + restore the `sql-js-wasm-robustness.md` name → live links auto-heal; move the bug spec to `.archive/`); this story migrates the one durable lesson from the post-mortem into the patterns doc. No version bump (doc-only; rides the next code release).

**Tasks:**

- [x] (developer) Un-archive and restore `docs/specs/sql-js-wasm-robustness.md` (original name → the `stories.md` Future item and `project-essentials.md` links resolve again; the doc's own `../../src/...` links are correct from `docs/specs/`). Move `bug-sql-js-browser-esm-spec.md` → `docs/specs/.archive/`.
- [x] Migrate the durable nugget into [sql-js-wasm-robustness.md](sql-js-wasm-robustness.md): add **Pattern F — CJS/ESM interop guard for the `initSqlJs` import** (the sql.js 1.13+ UMD browser-ESM breakage, the compounding `optimizeDeps.exclude` interaction, the two-part fix: VITEST-scoped exclude + typed `CjsEsmInteropError` guard), faithful to [database.ts:197-202](../../src/learningfoundry/sveltekit_template/src/lib/db/database.ts#L197-L202) and [vite.config.ts:27](../../src/learningfoundry/sveltekit_template/vite.config.ts#L27).
- [x] Add a cross-reference table row for the interop guard (Story J.y); extend the intro scope note; update "When to revisit" §3 to record that the export-shape drift already fired once (J.y) and now points at Patterns A **and** F. Pattern F links to the archived post-mortem for the full root-cause writeup.
- [x] Links verified: the two live references (`stories.md` Future item, `project-essentials.md` Story I.cc note) resolve to the restored path; no link edits needed after the rename.
- [x] No code/test change — documentation only.
- [x] **Follow-up (optional) — cross-link from the archived bug spec back to Pattern F.** A one-line "superseded by `sql-js-wasm-robustness.md` Pattern F" banner atop `.archive/bug-sql-js-browser-esm-spec.md` would orient anyone who lands on the post-mortem directly. Low value (archived, low traffic); deferred.

### Story K.d: v0.80.0 — Real `NbfoundryProvider` + `[nbfoundry]` extra + `status` handling [Done]

First story of the NbFoundry integration bundle (see [phase-k-1-nbfoundry-integration-plan.md](phase-k-1-nbfoundry-integration-plan.md)). Now that nbfoundry is published, add a real `ExerciseProvider` that delegates to `nbfoundry.compile_exercise`. Selection is per-block via a `status: stub | ready` field on the exercise block — reusing the existing `status` value space (the same word the compiled dict and `ExerciseBlock.svelte` already use), not a new property. `status` is the **single switch**, handled in the resolver: a `stub` block emits a placeholder dict directly (no provider call, no nbfoundry import); a `ready` block is compiled by the one `NbfoundryProvider`. There is **no two-provider fork** — `NbfoundryStub` is demoted to a test double / explicit injectable (e.g. a "no-notebooks" global override), not a routing target. Default `ready`, so a real exercise with a typo'd `ref` fails loud (fail-fast / OR-1) instead of silently degrading to a placeholder; `status: stub` is the explicit "not built yet" opt-in. Python-only and shippable alone — the existing thin `ready` renderer keeps drawing instructions+hints until K.f.

Feature → **minor** bump per Version Cadence.

**Tasks:**

- [x] `src/learningfoundry/integrations/nbfoundry.py` (new file, copyright header): `NbfoundryProvider` mirroring [`QuizazzProvider`](../../src/learningfoundry/integrations/quizazz.py). Keep `compile_exercise(ref_path, base_dir)` **signature-identical** to the `ExerciseProvider` protocol and nbfoundry's API — do **not** add a `status` param (it would diverge from `nbfoundry.compile_exercise(yaml_path, base_dir)` and break the protocol-match contract test; `status` is handled in the resolver, not here). Lazy `from nbfoundry import compile_exercise`; `ImportError` with a `pip install learningfoundry[nbfoundry]` hint; wrap any nbfoundry exception in `IntegrationError` citing `ref_path`. `NbfoundryStub` is retained as a test double / injectable only — not the default, not status-routed.
- [x] `pyproject.toml`: add `[project.optional-dependencies].nbfoundry = ["nbfoundry>=0.1"]` (floor mirrors the existing `quizazz>=0.1` extra, per developer decision) + a mypy `ignore_missing_imports` override for `nbfoundry`.
- [x] `src/learningfoundry/schema_v1.py` `ExerciseBlock`: add `status: Literal["stub", "ready"] = "ready"`. Keep the input enum's value space identical to the compiled-dict `status` and the TS type (Hidden Coupling: Pydantic input ↔ dict ↔ TS).
- [x] `src/learningfoundry/resolver.py`: handle `block.status` in one place — `"stub"` → emit the placeholder dict via a single factory (extracted `NbfoundryStub`'s placeholder logic into a module-level `stub_exercise(ref)` helper in `nbfoundry_stub.py` that both the resolver and the retained `NbfoundryStub` call); else → `exercise_provider.compile_exercise(ref, base_dir)`. One injected provider (default `NbfoundryProvider`); the stub path makes no provider call and imports no nbfoundry, so an all-`stub` curriculum never imports it. The status switch lives in the resolver, **not** in the provider method.
- [x] `tests/test_integrations/test_nbfoundry.py` (new): mock `nbfoundry.compile_exercise` (mirror `test_quizazz.py` — no nbfoundry install needed); cover delegation, `IntegrationError` wrapping, and the missing-package `ImportError` hint. Contract test asserts `NbfoundryProvider` satisfies the `ExerciseProvider` protocol — both a mypy-checked typed assignment (signature) and a runtime `isinstance` (the protocols are now `@runtime_checkable`).
- [x] `tests/` resolver coverage: `status: stub` emits the placeholder without invoking the provider (and without importing nbfoundry); `status: ready` (and default) invokes `NbfoundryProvider`; a `ready` block whose `ref` is missing fails loud (no silent stub fallback). Also covers the default-provider swap (a default-provider `ready` block routes to the real provider, not the stub).
- [x] Update `docs/specs/tech-spec.md` `ExerciseBlock` schema + `integrations/` listing to include `NbfoundryProvider` and the `status` field; kept `protocols.py` ↔ [consumer-dependency-spec.md](nbfoundry/consumer-dependency-spec.md) in sync (distribution table, versioning note, testing matrix).
- [x] `CHANGELOG.md` + version bump to v0.80.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.

### Story K.e: v0.81.0 — Exercise `id` + asset staging into `static/exercises/<id>/` [Done]

Second story of the bundle. Adds the explicit exercise `id` and the asset-staging pipeline step the integration needs. The `id` is the **build-output namespace** (`static/exercises/<id>/…`) and the progress key (`exerciseRef`) — it does **not** constrain where the author organizes source content (that stays free, located by the existing relative `ref`). Asset files referenced by a compiled exercise travel as relative paths in the dict's `assets: list[str]`; the pipeline copies them into the static output (per consumer-dependency-spec BR-5).

Feature → **minor** bump.

**Tasks:**

- [x] `src/learningfoundry/schema_v1.py` `ExerciseBlock`: add `id: str | None = None`, auto-derived from the `ref` stem (via an `autogen_id` model_validator) when omitted, with **curriculum-wide** uniqueness enforced at parse time (new `CurriculumDef.check_unique_exercise_ids` validator — the `id` is the asset URL + progress key, so it must be unique across the whole curriculum, not just per-module). Mirrors the `AssessmentDefinition.id` auto-gen precedent (Story J.r); a stem collision fails loud and the author sets an explicit `id`.
- [x] `src/learningfoundry/resolver.py`: after compiling a `ready` exercise, reads the dict's `assets: list[str]` and emits `Asset(source=base_dir/path, dest_relative="exercises/<id>/<path>")` into the existing `assets_by_dest` aggregator. Generalized the `Asset` docstring/dedup note — the dedup key is `dest_relative`, which holds for non-hashed exercise paths too.
- [x] `src/learningfoundry/generator.py`: added `"static/exercises"` to `_PRESERVED_PATHS` alongside `static/content`; confirmed (via test) the existing asset-copy loop stages exercise assets unchanged (it already writes any `dest_relative`); generalized the `_copy_assets` docstring for the non-hashed path.
- [x] `tests/`: resolver emits the expected `Asset` records for an exercise's `assets[]` (+ explicit-id namespacing + same-path dedup); generator copies them to `static/exercises/<id>/<path>` + preserves them across rebuild; `id` auto-derivation + curriculum-wide uniqueness (explicit-dup and stem-collision → parse error); stub exercises (and ready-without-assets) stage nothing.
- [x] Updated `docs/specs/tech-spec.md`: documented `static/exercises/<id>/` staging in the generator section (preserved set + step 3) and the `ResolvedCurriculum.assets` prose, and added the `id` field to the `ExerciseBlock` schema.
- [x] `CHANGELOG.md` + version bump to v0.81.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.

### Story K.f: v0.82.0 — `ExerciseBlock` ready renderer (manual-completion) + real `ExerciseContent` types [Done]

Third story of the bundle. Builds out the `ready`-state renderer that [ExerciseBlock.svelte](../../src/learningfoundry/sveltekit_template/src/lib/components/ExerciseBlock.svelte) currently stubs (it draws only instructions + hints today). Manual-completion flavor only — graded submission is deferred to `## Future`.

Feature → **minor** bump.

**Tasks:**

- [x] **(carryover from K.e) Resolver injects `content["id"] = block.id`** into the resolved exercise content (both stub and ready) so the frontend has the `/exercises/<id>/<path>` namespace + `exerciseRef` progress key; K.d stub-equality test updated; `stub_exercise()` gained `assets: []` for type consistency.
- [x] `src/learningfoundry/sveltekit_template/src/lib/types/index.ts` `ExerciseContent`: replaced the `unknown[]` placeholders with real `ExerciseSection` (title/description/code/editable) and the `ExpectedOutput` discriminated union (`image`→path/alt, `text`/`table`→content) shapes, plus `assets: string[]`, `id: string`, and a typed `ExerciseEnvironment`. Python-dict ↔ TS Hidden Coupling kept in lockstep with the compiled dict.
- [x] `ExerciseBlock.svelte` `ready` branch: renders `sections` (code blocks, read-only in v1 — the `editable` flag shows a "Your code here" badge but is reserved for the WASM future), `expected_outputs` (text/table inline; `type: image` via runtime-composed `/exercises/${content.id}/${path}` with `alt` + `loading="lazy"`), `hints`, and `environment` setup instructions.
- [x] "Mark as Complete" control → fires `oncomplete` `{ exerciseRef: id, status: "completed" }` + a no-arg `onexercisecomplete` (wired through `ContentBlock` → block completion) → writes `exercise_status` via `progressRepo.updateExerciseStatus(id, 'complete')`. (No scoring — `submission` is deferred.)
- [x] **Pin the open item — resolved: no runnable-notebook-location field in the v1 dict.** Per [consumer-dependency-spec.md](nbfoundry/consumer-dependency-spec.md) BR-1 + § "v1 Rendering Behavior", the Option-B (static) compiled dict carries no notebook path (`marimo_wasm_bundle` is the Option-A future field; "In v1 … execution happens externally"). The renderer therefore surfaces the code-scaffold `sections` + `environment.setup_instructions` and relies on the learner's cloned curriculum repo to run locally. (nbfoundry isn't installed in this env; the in-repo dependency-spec is the authoritative pin — option c.)
- [x] `vitest` coverage (`ExerciseBlock.test.ts`, 7 tests): ready renderer draws sections/expected_outputs(text)/hints/environment; image outputs compose the `/exercises/<id>/<path>` URL with alt + lazy; "Mark as Complete" fires the event and records `exercise_status`; stub status still renders the placeholder (no sections, no complete button).
- [x] Updated `docs/specs/features.md` FR-6 (nbfoundry integration) rendering behavior + the stale v1-limitation note, and `tech-spec.md` `ExerciseContent`/`ExpectedOutput` types to match (added `id`, `assets`, discriminated `ExpectedOutput`).
- [x] `README.md` — added an "Authoring nbfoundry exercises" section (author-facing): referencing an exercise (`source: nbfoundry`, `ref`, `status: stub|ready`), how `id` works (auto-derived from the `ref` stem, curriculum-wide unique), worked source-vs-flat-output examples, the stem-collision case that forces an explicit `id`, and why a stable `id` keeps asset URLs + progress intact across source reorganization. Also added the `[nbfoundry]` install extra.
- [x] `CHANGELOG.md` + version bump to v0.82.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.

---

## Subphase K-2: Refactor NbFoundry Integration, Launch Marimo, Open in a New Window

**Rendering approaches.** This subphase changes how nbfoundry exercises render. Three approaches were considered — full write-up in [consumer-dependency-spec.md § "Design Decision: Rendering Approach"](nbfoundry/consumer-dependency-spec.md). The story tasks below reference these by name:

- **Option A — Marimo-WASM embed:** run the notebook in-browser via Pyodide. Out for v1 (PyTorch isn't available under Pyodide); revisit for non-GPU exercises.
- **Option B — Static display** (shipped K.d–K.f, now retired): nbfoundry compiled the exercise to a static dict (`sections`/`expected_outputs`) that LF rendered read-only. It failed in practice — a model-building exercise rendered statically is just the notebook's *source code* in a `<pre>` block, with no executed cells, plots, or metrics.
- **Option C — Locally-hosted live marimo + banner/launch** (this subphase): nbfoundry emits a runnable marimo `.py` + banner metadata; LF stages the notebook + an `exercises-manifest.json` sidecar; the learner runs `learningfoundry launch <id>` (a CLI that owns marimo's lifecycle — a static browser page can't spawn or kill a process) and the app shows a banner linking to the live notebook.

**Phase-bundled release:** K.g–K.i run **unversioned**; the single **minor** bump (**v0.83.0**) lands on the last story, **K.j**.

**Dependency / risk:** nbfoundry must implement the Option-C contract (return `notebook_source` + metadata; **codegen MUST be torch-free** — torch is a learner-runtime dep only). Until it ships, the provider is exercised against a mocked contract (as K.d mocked `compile_exercise`).

---

### Story K.g: Option C contract + `NbfoundryProvider` rewrite + `ExerciseBlock.mode` [Done]

Build side, part 1 — define the new shape. Rewrites the nbfoundry dependency-spec to Option C, changes the provider's return shape (metadata + notebook source, no static-render fields), and adds the per-exercise `mode`. No staging yet (K.h). Unversioned (rides K.j).

**Decisions (locked):** `mode` default = **`edit`** (author-overridable per exercise). The exercises manifest is a **sidecar `exercises-manifest.json`** (build output at the project root, not under `static/`) — keeps the CLI's `id → notebook_path/mode/port` read cheap and decoupled from the frontend's `curriculum.json`, and keeps the notebook's filesystem path out of the browser payload.

**Tasks:**

- [x] `docs/specs/nbfoundry/consumer-dependency-spec.md`: replaced the Option-B compile contract with **Option C**. Rewrote the "Design Decision" section (Option C is v1; Option B marked SUPERSEDED; Option A future/PyTorch-blocked) and **BR-1** — `compile_exercise(yaml_path, base_dir) -> {title, description, hints, mode, environment, notebook_source}`, dropped `sections`/`expected_outputs`/`submission`/`instructions`, added the explicit *codegen MUST NOT import torch/modelfoundry; torch is learner-runtime only* constraint. Added a consolidated superseded-section note pointing BR-4/BR-5/RR-1's static-render details at K.i/K.j.
- [x] `src/learningfoundry/schema_v1.py` `ExerciseBlock`: added `mode: Literal["edit", "run"] = "edit"`. `id`/`status` unchanged.
- [x] `src/learningfoundry/integrations/nbfoundry.py` `NbfoundryProvider.compile_exercise`: **no code change needed** — it was already a pure pass-through (K.d), so it carries the Option-C dict (metadata + `notebook_source`) verbatim. Lazy import + `ImportError` hint + `IntegrationError` wrap intact.
- [x] `tests/`: `test_nbfoundry.py` `_MOCK_EXERCISE` updated to the Option-C shape + asserts `notebook_source`/`mode` pass through and `sections`/`expected_outputs` are absent; `test_schema_v1.py` covers `mode` default (`edit`) + explicit `run` + rejects unknown. 456 passed; ruff + mypy clean.
- [x] No version bump (phase-bundled; rides K.j).

### Story K.h: Notebook staging + exercises manifest (resolver + generator) [Planned]

Build side, part 2 — produce the build artifacts. The resolver hands `notebook_source` to a runnable staging path keyed by `id` and emits a manifest entry; the generator writes the `.py` + manifest; the static `sections`/`expected_outputs` aggregation is retired. Unversioned (rides K.j).

**Tasks:**

- [ ] `src/learningfoundry/resolver.py` (`ready` exercise): (a) hand `notebook_source` to a **runnable staging path** keyed by `id` — **not** under `static/` (a `.py` the learner `marimo`-runs, e.g. `exercises/<id>/<id>.py` in the generated project); (b) emit an **exercises-manifest** entry `{id, notebook_path, mode, port}`; (c) keep injecting `content["id"]` + the banner metadata into the resolved content for K.j; (d) retire the `sections`/`expected_outputs` aggregation. Stub exercises stage no notebook.
- [ ] `src/learningfoundry/generator.py`: write the notebook `.py` to its runnable location (preserved across rebuilds, **not** web-served `static/`); write the `exercises-manifest.json` sidecar (id → `notebook_path`/`mode`/`port`) at the project root.
- [ ] **K.e asset-staging fate:** decide whether `static/exercises/<id>/` image staging survives (only if a banner/notebook references served images) or is retired with the static renderer. Record the decision.
- [ ] `tests/`: resolver stages the notebook to the runnable path + emits the manifest entry + retains `id`/metadata; generator writes the `.py` + manifest + preserves them across a rebuild; stub stages nothing.
- [ ] Update `docs/specs/tech-spec.md`: the exercise-dict shape change (metadata + notebook path + mode, no sections/expected_outputs), the notebook staging + manifest in the generator section.
- [ ] No version bump (phase-bundled; rides K.j).

### Story K.i: `learningfoundry launch` / `stop` CLI (Launch Marimo) [Planned]

The learner-side runtime that owns marimo's lifecycle — the piece that lets a static app drive a live notebook without the browser spawning processes. Cross-platform Python (a CLI subcommand, **not** a shell script — Windows has no bash). Unversioned (rides K.j). *Flesh fully at its gate.*

**Tasks (sketch):**

- [ ] `src/learningfoundry/cli.py` `learningfoundry launch <exercise-id>`: resolve `id → notebook_path / mode / port` from the manifest; socket-probe the port; read/write a pidfile (e.g. `.learningfoundry/launch-<port>.pid`); if the port is held by a **launch-owned** marimo, prompt to kill/replace (never blind-kill foreign processes); spawn `marimo edit|run <path> --headless -p <port> --no-token` per `mode`.
- [ ] `learningfoundry stop [<exercise-id>]`: tear down the launch-owned marimo via the pidfile.
- [ ] `tests/`: id→path/mode resolution from the manifest; port-in-use → prompt/replace; pidfile lifecycle; correct marimo argv per `mode` (mock subprocess/socket); cross-platform path handling.
- [ ] No version bump (phase-bundled; rides K.j).

### Story K.j: v0.83.0 — `ExerciseBlock` banner (Open in a new window) + retire static renderer [Planned]

Final story; owns the **v0.83.0** release for the whole subphase. The frontend `ready` renderer becomes the 4-state banner card (Copy CLI → Open Exercise → Mark Complete → done) and the static sections/expected_outputs renderer + dead `ExerciseContent` fields are removed. *Flesh fully at its gate.*

**Tasks (sketch):**

- [ ] `src/learningfoundry/sveltekit_template/src/lib/types/index.ts` `ExerciseContent`: replace `sections`/`expected_outputs` with the banner shape (title/description/hints/`launch_command`/`url`/mode/id); drop the now-dead fields.
- [ ] `ExerciseBlock.svelte` `ready` branch → 4-state banner: **Copy CLI Command** (clipboard `learningfoundry launch <id>`, transient "Copied ✓") → **Open Exercise ↗** (new tab to `http://localhost:<port>`) → **Mark as Complete** (writes `exercise_status`, fires completion — reuses K.f wiring) → complete slate (derived on load from `exercise_status`). Command text stays visible/re-copyable. Stub still renders the placeholder.
- [ ] `vitest`: 4-state flow; clipboard writes the exact `learningfoundry launch <id>` string; Open targets the right URL; Mark Complete records `exercise_status` + fires events; stub placeholder.
- [ ] Update `docs/specs/features.md` FR-6 + `README.md` authoring section (the launch flow + `learningfoundry launch`/`stop`); `tech-spec.md` `ExerciseContent` banner shape.
- [ ] `CHANGELOG.md` + **version bump to v0.83.0** in `pyproject.toml` and `src/learningfoundry/__init__.py` (the subphase release).

---

## Subphase K-3: Assessment Scoring, Reporting, and Bug Fixes

- **`AssessmentScore` shape + `assessment_scores` table reconciliation — capture in `project-essentials.md` once J.u lands.** Story J.u's investigation task picks between "add `(module_id, assessment_id)` columns to the existing `assessment_scores` table" and "introduce a separate `module_assessment_scores` table." Whichever path lands, the rationale and the why-not of the rejected alternative belong in [project-essentials.md](project-essentials.md) under "Domain Conventions" alongside the existing "Assessment scores — aggregate only in learningfoundry" entry. Deferred from the J sub-phase project-essentials sweep because the choice isn't concrete yet; capture it as part of J.u's wrap-up or a follow-up cleanup story rather than letting it slip.
- **Curriculum completion screen** — "Course Complete" celebration page reached after the last lesson's Finish


---

## Future

<!--
This section captures items intentionally deferred from the active phases above:
- Stories not yet planned in detail
- Phases beyond the current scope
- Project-level out-of-scope items
The `archive_stories` mode preserves this section verbatim when archiving stories.md.
-->

- **Graded exercise submission.** The optional `submission` block (typed input fields + the locked `range`/`equals`/`contains_all` scoring formula + score storage). Deferred from Subphase K-1 — K.f ships the manual-completion ("Mark as Complete") path first. Forward-compatible by design: the `submission` schema is the author's success contract independent of *how* values are captured, so adding it later needs no exercise-YAML rewrites. Revisit after the manual-completion path proves out; it forces a score-storage decision (a score column on `exercise_status` vs. a parallel `exercise_scores` table mirroring `assessment_scores`). See [nbfoundry/consumer-dependency-spec.md](nbfoundry/consumer-dependency-spec.md) § submission block.
- **Marimo WASM exercise embed ("Option A").** In-browser notebook execution via Pyodide, replacing the v1 local-run + manual-completion flow. Deferred from K-1; the v1 contract is forward-designed (the same `submission` schema is satisfied by Marimo cell outputs) so authored exercises don't need rewriting when it lands. Cons noted in the dependency spec: ~40MB Pyodide payload, cold-start latency, no PyTorch/GPU under WASM. Revisit for non-GPU exercises.
- **Curriculum application bundle.** v1 distributes the entire curriculum (the LearningFoundry app + toolchain: quizazz, nbfoundry, DataRefinery, modelfoundry + all authored artifacts) via `git clone`. A packaged/installable application bundle is deferred until distribution beyond clone is needed.
- **lmentry integration** — Direct LLM invocation for content generation (currently done externally)
- **d3foundry real integration** — Replace `D3foundryStub` with D3.js visualization generation when d3foundry is published
- **Reset button** — Course / module / lesson progress reset; defined in sub-plan, deferred from I.j
- **Lesson-level `locked` override** — Per-lesson explicit lock/unlock field in `curriculum.yml`; module-level and sequential rules cover v1 cases
- **Locked lesson tooltip** — Explanation shown when a learner clicks a locked lesson item
- **Non-YouTube video providers** — Vimeo, self-hosted; VideoBlock currently dispatches `videocomplete` via YouTube IFrame API or viewport fallback only
- **Progress export/import** — Sync or backup learner progress
- **`lessonresume` lifecycle event** — Revisits to lessons already at `complete`. Distinct from `lessonopen` (which fires on every mount including resumes) because it carries the additional invariant "previously completed." Useful for analytics on review behaviour. Deferred from FR-P15 / Story I.p — the data is derivable today from `(getLessonProgress before mount).status === 'complete'`, so the event is sugar rather than new capability.
- **Lifecycle timestamps** — `opened_at`, `engaged_at` columns symmetric with the existing `completed_at`. Deferred from FR-P15 with the explicit reasoning that adding one timestamp at a time yields asymmetric coverage; a coherent treatment covers all transitions, picks a retention/decimation policy, and integrates with whatever telemetry/export story is current at the time.
- **Spaced repetition / adaptive sequencing**
- **Multi-curriculum dashboard**
- **Advanced Testing Infrastructure** - See docs/specs/future-testing-infra-plan.md
- **`pnpm publish` OIDC trusted-publishing gap (upstream).** `pnpm publish` forwards `--provenance` (sigstore signing succeeds and is visible in workflow logs) but skips the GitHub-OIDC-token-for-npm-publish-token exchange — the actual `PUT` to the npm registry then 404s expecting a stored `NPM_TOKEN`. Workaround: drive the publish step with `npm publish` directly while keeping `pnpm` for install/build/validate (this is what quizazz's CI does — see quizazz Story M.f). Worth filing upstream against pnpm; no impact on learningfoundry today since we don't publish to npm. Revisit if learningfoundry ever ships an npm package, or if pnpm closes the gap.
- **Configurable curriculum-style templates.** Phase-J-deferred Feature 4 from [phase-j-pedagogical-authoring-plan.md](phase-j-pedagogical-authoring-plan.md). Different curriculum genres want different pedagogical commitments — a boot-camp curriculum might require every lesson to declare a duration and a role; a self-study curriculum might require nothing. Hard-coding required `meta` fields in `schema_v1.py` is wrong for both. A style template is a curriculum-level config (`curriculum.style: <name-or-path>`) that declares which `meta` fields are required, which `role` values are allowed, and which assessment positions are expected per role. Built-in styles to ship: `minimal` (no meta required, no assessment expectations) and `narrative-survey` (opinionated meta, three-quiz model expected). Validation runs as a layer after Pydantic schema validation. Deferred from Phase J because it depends on Features 1–3 having stabilized; revisit once two or more curricula have authored against the J.a/d/e shapes and the constraint vocabulary is empirically obvious.
- **TypeScript-from-Pydantic type generator.** Eliminate the hidden coupling between [schema_v1.py](../../src/learningfoundry/schema_v1.py) and `lib/types/index.ts` (and between provider return-dict shapes and their TS counterparts) by generating TS types from Pydantic models via `pydantic2ts` (or equivalent) and failing CI when the generated output is stale. Two-part scope: (a) generate from existing Pydantic models in `schema_v1.py`; (b) promote provider return shapes (`ExerciseContent`, `VisualizationContent`, `QuizManifest`) to Pydantic so they're generatable too. Best landed after Phase J ships its expanded meta + assessments schema so the generator covers the full surface from day one. Discriminated unions (content blocks, assessment positions) need explicit Pydantic discriminator config to round-trip cleanly.
- **Polymorphic `<AssessmentBlock>` provider dispatch.** `<AssessmentBlock>` is currently a direct wrapper around `<QuizBlock>` (post-J.m.5). When a second `AssessmentProvider` materializes (LLM interview, interactive game, etc.), the wrapper should select the concrete vendor component from `manifest.source` (or equivalent discriminator) instead of importing `<VendorQuizBlock>` directly. Deferred from J.m.6 (quizazz vendor-pushback § "Recommended change 2"): building one-branch dispatch logic pre-1.0 with one provider is speculative scaffolding. Documented as a forward note in `consumer-dependency-spec.md` RR-1b. Revisit when a second provider exists; the current direct-import design is forward-compatible with the change.
- **`<AssessmentBlock>` wrapper upward-re-emit refactor.** The wrapper currently persists internally via `progressRepo.saveAssessmentScore(...)` and fires a no-arg `onassessmentcomplete?.()` upward. Quizazz's vendor-pushback envisioned an alternative where the wrapper translates the event detail (`quizRef → assessmentRef`) and re-emits a typed `AssessmentCompleteEvent` payload `{assessmentRef, score, maxScore, questionCount}` upward, letting the consumer own persistence — symmetric with RR-1a's pure-translation-surface model on the Python side. Deferred from J.m.6 (quizazz vendor-pushback § "Recommended change 5" / RR-1b clause 2): pre-1.0 with one consumer, the inversion adds two footguns (silent score loss if a future consumer forgets to wire persistence; async-ordering for downstream UI dependent on a persisted score) with no current benefit. Documented as a forward note in `consumer-dependency-spec.md` RR-1b. Revisit when a second `<AssessmentBlock>` consumer materializes (preview route, authoring sandbox, alternate persistence backend); the current no-arg callback shape is forward-compatible with adding a typed parameter.
- **Sql.js wrapper library extraction.** Both learningfoundry and quizazz consume `sql.js`. The robustness patterns (HEAD-fetch precheck, typed `WasmAssetMissingError`, init memoization, repo-boundary swallow) are documented at [sql-js-wasm-robustness.md](sql-js-wasm-robustness.md). Deliberately *not* extracted into a `@pointmatic/sql-js-kit` package today: N=2 is the classic premature-abstraction trap, the genuinely shared surface is ~60 lines, and the partitioning / UI-surface decisions diverge sharply between the two consumers. Revisit when a third consumer appears, or when learningfoundry and quizazz independently grow mirroring features (schema versioning, multi-DB, sync). Patterns doc travels in the meantime.
