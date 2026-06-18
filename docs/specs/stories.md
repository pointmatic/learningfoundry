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

### Story K.e: v0.81.0 — Exercise `id` + asset staging into `static/exercises/<id>/` [Planned]

Second story of the bundle. Adds the explicit exercise `id` and the asset-staging pipeline step the integration needs. The `id` is the **build-output namespace** (`static/exercises/<id>/…`) and the progress key (`exerciseRef`) — it does **not** constrain where the author organizes source content (that stays free, located by the existing relative `ref`). Asset files referenced by a compiled exercise travel as relative paths in the dict's `assets: list[str]`; the pipeline copies them into the static output (per consumer-dependency-spec BR-5).

Feature → **minor** bump.

**Tasks:**

- [ ] `src/learningfoundry/schema_v1.py` `ExerciseBlock`: add `id: str | None = None`, auto-derived from the `ref` stem when omitted, with **curriculum-wide** uniqueness enforced at parse time (the `id` is the asset URL + progress key, so it must be unique across the whole curriculum, not just per-module). Mirror the `AssessmentDefinition.id` auto-gen precedent (Story J.r); a stem collision fails loud and the author sets an explicit `id`.
- [ ] `src/learningfoundry/resolver.py`: after compiling a `ready` exercise, read the dict's `assets: list[str]` and emit `Asset(source=base_dir/path, dest_relative="exercises/<id>/<path>")` into the existing `assets_by_dest` aggregator. Generalize the `Asset` docstring/dedup note — the dedup key is `dest_relative`, which holds for non-hashed exercise paths too.
- [ ] `src/learningfoundry/generator.py`: add `"static/exercises"` to `_PRESERVED_PATHS` alongside `static/content`; confirm the existing asset-copy loop stages exercise assets unchanged (it already writes any `dest_relative`).
- [ ] `tests/`: resolver emits the expected `Asset` records for an exercise's `assets[]`; generator copies them to `static/exercises/<id>/<path>`; `id` auto-derivation + curriculum-wide uniqueness (collision → parse error); stub exercises (empty `assets`) stage nothing.
- [ ] Update `docs/specs/tech-spec.md`: document `static/exercises/<id>/` staging in the generator section and the `id` field in the `ExerciseBlock` schema.
- [ ] `CHANGELOG.md` + version bump to v0.81.0 (developer-driven release step).

### Story K.f: v0.82.0 — `ExerciseBlock` ready renderer (manual-completion) + real `ExerciseContent` types [Planned]

Third story of the bundle. Builds out the `ready`-state renderer that [ExerciseBlock.svelte](../../src/learningfoundry/sveltekit_template/src/lib/components/ExerciseBlock.svelte) currently stubs (it draws only instructions + hints today). Manual-completion flavor only — graded submission is deferred to `## Future`.

Feature → **minor** bump.

**Tasks:**

- [ ] `src/learningfoundry/sveltekit_template/src/lib/types/index.ts` `ExerciseContent`: replace the `unknown[]` placeholders with real `sections` (title/description/code/editable) and `expected_outputs` (description/type/path|content/alt) shapes, plus `assets: string[]`. This is the Python-dict ↔ TS Hidden Coupling — keep it in lockstep with the compiled dict.
- [ ] `ExerciseBlock.svelte` `ready` branch: render `sections` (code blocks, read-only in v1 — the `editable` flag is reserved for the WASM future), `expected_outputs` (text/table inline; `type: image` via runtime-composed `/exercises/${id}/${path}` with `alt` + `loading="lazy"`), and `hints`.
- [ ] "Mark as Complete" control → fire the `complete` event `{ exerciseRef: id, status: "completed" }` → write `exercise_status` via the progress repo. (No scoring — `submission` is deferred.)
- [ ] **Pin the open item:** confirm against the released nbfoundry whether the compiled dict carries a runnable-notebook location. If yes, surface it ("open `<relative-path>` and run locally"); if no, rely on the rendered `sections` + the learner's cloned curriculum repo. Record the resolution in this story.
- [ ] `vitest` coverage: ready renderer draws sections/expected_outputs/hints; image outputs compose the `/exercises/<id>/<path>` URL; "Mark as Complete" fires the event and records `exercise_status`; stub status still renders the placeholder.
- [ ] Update `docs/specs/features.md` FR-6 (nbfoundry integration) rendering behavior and `tech-spec.md` `ExerciseContent` types to match.
- [ ] `README.md` — add an "Authoring nbfoundry exercises" section (author-facing) covering the end-to-end workflow: referencing an exercise (`source: nbfoundry`, `ref`, `status: stub|ready`), how `id` works (auto-derived from the `ref` stem, curriculum-wide unique), and **worked examples** of organizing content freely vs. the flat `static/exercises/<id>/` output — including the `exercise.yml`-stem collision case that forces an explicit `id`, and that a stable `id` keeps asset URLs + progress intact across source reorganization. (This is the author-facing home for the `id`-vs-source-layout guidance — instructive to the curriculum author, not an LLM must-know.)
- [ ] `CHANGELOG.md` + version bump to v0.82.0 (developer-driven release step).

---

## Subphase K-2: Assessment Scoring, Reporting, and Bug Fixes

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
