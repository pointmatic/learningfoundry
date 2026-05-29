# phase-f-pyve-named-testenvs.md — Use cases for named / multiple test environments in pyve

**Status:** Context brief for a **pyve** planning phase (drafted from an nbfoundry session, 2026-05-29; revised from a learningfoundry-side review, 2026-05-28). **Not** a design or implementation spec — pyve owns the design. This doc supplies the use cases, the requirements they imply, and the open questions, so pyve can plan a proper, comprehensive, *general* solution.
**Audience:** pyve maintainers (planning input).
**Origin:** surfaced while fixing the silent-skip "testenv trap" — see `phase-f-pyve-micromamba-testenv-trap.md` (the motivating case study) and story **F.f.1** in `stories.md`.
**Revision bias (2026-05-28).** The current revision was driven by a review of **learningfoundry's** testing topology, which is a *weaker* case for named testenvs than nbfoundry's hardware-smoke (learningfoundry's pain concentrates on the Node/vitest/playwright side, which is correctly outside pyve's stated scope; see UC5 and "Position on the value spectrum" below). Weight the originating nbfoundry use cases (UC1, UC4) higher than learningfoundry's marginal fit when prioritizing design.

---

## The core insight

pyve today models **one main env + one test env** (the test env a plain `python -m venv`). But a non-trivial project routinely has **more than one
test *category*, each with materially different environment needs** along one or more axes:

- **Dependency weight** — a light lint/unit set vs. a multi-GB stack.
- **Backend** — pip/venv vs. conda/micromamba (native libs, channel-only pkgs).
- **Runtime / target platform** — cross-platform CI vs. hardware-gated (e.g. Apple-Silicon-only) smokes; or DOM vs. server runtimes in JS land.
- **Manifest source** — the deps come from `requirements*.txt`, a `pyproject` extra, or a conda `environment*.yml`.

With a single test env, you are forced to either (a) make that one env the union of all needs — bloating routine runs with deps they never exercise — or (b) keep it minimal and push the other categories out of band (separate hand-built directories, `pyve run python -m pytest` incantations, etc.). Both are what bit nbfoundry. The general fix is letting a project **declare multiple, named test environments**, each with its own backend and manifest, and select which one a given test run uses.

### Already shipped (build on, don't re-litigate)

pyve already added, in response to the trap:

- **`pyve test --env main`** — a two-value env selector (`testenv` default, `main` opt-in).
- **Silent-skip advisory** + `PYVE_NO_TESTENV_ADVISORY=1`.

The capability below is, in large part, the **generalization of `--env`** from a fixed {`testenv`, `main`} pair into an arbitrary set of named environments — plus per-env backend and manifest configurability.

---

## Use cases

Each use case states the scenario, what the project needs, why the current one-test-env model fails it, and the capability it implies.

### UC1 — Heavy hardware-smoke env vs. light CI env (the nbfoundry case)

**Scenario.** nbfoundry has two test categories: (a) ~dozen hardware-*independent* unit/lint/type checks that run in CI on any platform every push; (b) `@pytest.mark.hardware` smokes that need a multi-GB ML stack (PyTorch+MPS, TensorFlow-Metal, Keras, HuggingFace) and run only manually on Apple Silicon.

**Need.** A **light** test env for (a) and a **heavy** test env for (b), so CI never downloads/installs gigabytes of a stack it deselects and never executes.

**Why current model fails.** One test env forces a choice: heavy (taxes every CI run) or light (no in-repo home for the smoke stack → the separate-directory workaround).

**Implies:** named test environments; lazy/opt-in provisioning (the heavy env is only built when that category is run); per-invocation env selection.

### UC2 — Test/runtime parity when the runtime is conda (the trap's root cause)

**Scenario.** The runtime/main env is micromamba (conda-forge resolution). The venv test env resolves a *different* dependency graph (pip wheels), so tests can pass against a graph that differs from what actually ships/runs.

**Need.** A test env that resolves **the same way the runtime does** — same backend, ideally same lock.

**Why current model fails.** The test env is venv-only; it cannot mirror a conda main env. This divergence is a cousin of the duplicate-TensorFlow / standalone-Keras hygiene problem found in F.f.1.

**Implies:** per-test-env **backend selection**, with the ability to **inherit the main env's backend** by default.

### UC3 — Conda-managed native/system test dependencies

**Scenario.** Tests must import a package whose native deps are painful or unavailable via pip wheels but clean via conda-forge — GDAL/GEOS/PROJ (geospatial), CUDA toolkit, MKL/BLAS variants, HDF5, ffmpeg — or must invoke a **non-Python** binary at test time (a database, a compiler, node).

**Need.** A conda-backed test env (and/or one that can carry non-Python tools).

**Why current model fails.** A `python -m venv` test env can only pip-install Python wheels; it cannot provision conda-only native libs or system binaries.

**Implies:** conda/micromamba as a selectable test-env backend.

### UC4 — Validating a bundled payload manifest (fidelity, anti-drift)

**Scenario.** The artifact under test *is* a shipped manifest — nbfoundry's `src/nbfoundry/templates/environment.yml`, the conda env every scaffolded student project receives. The smoke's entire purpose is to prove **that exact manifest** produces a working stack on real hardware.

**Need.** Build the test env **from that same manifest** (not a hand-maintained parallel file that can drift). If a separate dev manifest is used, a guard that flags divergence from the shipped one.

**Why current model fails.** No way to point a test env at an arbitrary `environment.yml`; the venv test env is built from pip manifests only, so the shipped conda manifest can't be the source of truth for what's tested.

**Implies:** test envs buildable from an **arbitrary, project-named manifest** (`environment*.yml` or `requirements*.txt`); optionally a drift check when the test manifest is meant to equal a shipped one.

### UC5 — Polyglot / non-Python runtimes (explicit scope honesty marker; out of scope for v1)

**Scenario.** A SvelteKit app with an API surface has component tests in jsdom/Playwright and API/server tests in plain Node. Generalizing: a project whose test surface spans Python + a non-Python runtime (Node, Go, a CLI shell-out). learningfoundry's SvelteKit template is exactly this shape.

**Why it's listed.** A learningfoundry-side review confirmed this case is real in polyglot repos, but pyve's **stated charter** makes non-Python runtime management a deliberate non-goal: `concept.md` calls it "Pyve: Python Virtual Environment Manager"; the explicit out-of-scope list includes "Docker container or cloud environment management"; the primary value metric is Python time-to-hello-world. Honest framing: UC5 documents *why this is hard* and that the named-env primitive is not the right place to fix it.

**Position for v1.** Out of scope. Ship pytest-only, Python-only. The only ask on v1 is that the design **not actively preclude** later evolution — in particular, the per-env "what command runs the tests" hook should not hard-code `pytest` as a syntactic singleton, even if v1 supports nothing else.

**Where polyglot grief actually lives.** Polyglot orchestration belongs in a separate tool (or a separate, scoped pyve expansion with its own charter discussion). The named-env primitive should not be loaded with this responsibility.

### UC6 — Matrix testing (scope-question only; design must not preclude)

**Scenario.** Run the same suite against multiple dependency sets or interpreters (torch 2.5 vs 2.6, py3.11 vs 3.12) to catch version-specific breakage.

**Position.** v2+ scope decision; **out of scope for v1.** Named envs are the natural substrate for a matrix layer above them — the only ask of v1 is to avoid singleton assumptions in selection, naming, and config schema that would prevent a future matrix layer from composing on top.

---

## Requirements distilled from the use cases

These are the *properties* a general solution should have. Mechanism/syntax is pyve's to design.

1. **Multiple, named test environments per project.** Declarable in pyve config; `--env <name>` selects one (strict generalization of the shipped `--env {testenv,main}`).
2. **Reserved names — `main` and `testenv`.** The shipped `pyve test --env main` / `--env testenv` semantics must survive verbatim. `main` = the project's main env (today's behavior); `testenv` = the default unnamed testenv at `.pyve/testenv/venv/` (today's `--env testenv` behavior). Both names are reserved in the generalized namespace — projects cannot redeclare or shadow them. Zero-migration property: every currently-shipped invocation keeps working unchanged.
3. **Per-env backend.** At least venv and micromamba; a test env should be able to **inherit the main env's backend** by default (UC2).
4. **Per-env manifest source.** `requirements*.txt`, a `pyproject` extra, or an arbitrary `environment*.yml` (UC3, UC4).
5. **Light default preserved.** The pure-Python majority keeps a single light venv test env with zero added ceremony. Named/heavy/conda envs are
   **opt-in** (don't tax simple projects).
6. **Lazy provisioning.** A heavy env is built/installed only when a run actually targets it; CI selects the light env and never materializes the heavy one (UC1).
7. **Fidelity / anti-drift.** Support building a test env from the *same* manifest as the artifact under test, ideally with a divergence check (UC4).
8. **Generalize the Story M.c silent-skip advisory to N envs.** The trap's first instance already shipped a remedy (the testenv-vs-main advisory and `PYVE_NO_TESTENV_ADVISORY=1` escape hatch, [features.md FR-11](pyve/features.md)). Generalize the same surfacing discipline to named envs: when a selected env appears wrong for the suite (mass `importorskip`-driven skip, marker selects nothing, env not provisioned), advise loudly at invocation time. Requires a config-declared notion of "what this env should have collected" — declared markers, file globs, or an explicit `tests:` block per env — so the advisory has ground truth to compare against. Silent fallback is the trap by another name; this requirement exists to prevent regrowing it at N×.
9. **Composition with pytest selection (`-m`, `-k`).** Specify how `--env <name>` composes with pytest's own selection. **Recommended semantics: AND.** `pyve test --env smoke -m slow` = *slow-marked tests in the smoke env*. Composition must be deterministic and documented — CI matrices and orchestrator scripts depend on it.
10. **Per-env diagnostics via `pyve check`.** [features.md FR-5](pyve/features.md) currently surfaces "testenv pytest status" as a single check. Generalize to iterate declared envs: each env's existence, backend, manifest staleness, and pytest-importability reported separately. The existing exit-code ladder (0 pass / 1 error / 2 warn) extends cleanly; per-env findings roll up to the worst.
11. **Registry UX — list and typo-guidance.** `pyve testenv list` to enumerate declared envs and their state (exists, backend, last-built, advisory status). `pyve test --env <typo>` returns a typo-guidance error suggesting reserved names and declared envs — never silent fallback to a default. Silent fallback was the original trap; do not regrow it in the named-env layer.
12. **Coherent selection across CLI/CI.** One obvious way to pick the env in a `pyve test` invocation and in CI config; sensible default when unspecified (recommended default: `testenv`, matching today's omitted-flag behavior).

---

## Position on the value spectrum — weighting the source projects

Different projects motivate this capability with different strength of need. When prioritizing v1 design choices, weight accordingly:

- **nbfoundry — strongest case.** Hardware-smoke (UC1) + manifest fidelity for the shipped `environment.yml` (UC4) + conda runtime parity (UC2). The originating story F.f.1 is here. The trap that motivated the doc landed here first.
- **learningfoundry — weak-to-moderate case.** One clean fit: replace the triple kill-switch on the SvelteKit smoke ([`pyproject.toml`](../../pyproject.toml) `addopts = "--ignore=tests/test_smoke_sveltekit.py"` + `@pytest.mark.smoke` + `SKIP_SMOKE` env var) with one declarative named-env selector. **The larger pains in learningfoundry's testing surface — vitest config quirks, jsdom browser-conditions gating, playwright orchestration, pnpm provisioning — sit on the Node side and are correctly outside pyve's stated scope (UC5).** Net value to learningfoundry from this feature is modest. If quizazz ever ships real (vs. the current stub providers), an `--env integration` carrying the `[quizazz]` extra becomes a second clean fit — still Python-only, still in charter.
- **Implication for design.** If a design choice trades cleanness of the Python+pytest path against speculative non-Python generality, **favor the Python+pytest path.** The strongest documented cases (nbfoundry UC1/UC2/UC4) all live there. UC5 is documented for honesty, not as a v1 requirement.

## Explicitly out of scope (for pyve, from nbfoundry's view)

- **Co-residence process isolation.** nbfoundry's hardware smokes must run **one test file per process** (PyTorch-MPS and TensorFlow-Metal SIGBUS when co-resident — story F.f.1). That is a *pytest execution* concern (per-file invocation / `pytest-forked`), **orthogonal** to env topology. Named test envs neither cause nor fix it; pyve should not conflate the two.
- **Implementation specifics** — config schema, command names, lockfile handling, env storage layout. All pyve's to decide. The illustrative `--env <name>` above is descriptive, not prescriptive.

## Open questions for pyve's planning phase

1. **How do named envs unify with the shipped `--env main` / `--env testenv`?** — **Recommended answer (Req 2): reserve both as well-known names** in the generalized namespace, semantics unchanged. Open sub-question: does pyve want a third reserved name (`default`?) for the implicit selection when `--env` is omitted, or is "omitted = `testenv`" sufficient? Recommendation: keep "omitted = `testenv`"; do not introduce `default` — it adds a name without earning one.
2. **Config location** — `[tool.pyve.testenvs]` in `pyproject.toml`, a pyve-native config, or per-manifest convention? — **Recommended answer: extend `.pyve/config`.** [README.md "Project Configuration File"](pyve/README.md) and [features.md "Project Config File"](pyve/features.md) already establish `.pyve/config` as YAML with top-level `backend:`, `micromamba:`, `python:`, `venv:` keys. A `testenvs:` block fits cleanly and preserves the "one place projects look for pyve config" property. `pyproject.toml` would split config across two files and break for non-pyproject projects (bash scripts, raw `requirements.txt`-only projects).
3. **Backend inheritance default** — does a test env default to the main env's backend, or to venv, with conda as explicit opt-in? *(genuinely open)*
4. **Matrix scope** (UC6) — **Recommended position: out of scope for v1; design must not preclude.** See UC6.
5. **Generality boundary** (UC5) — **Recommended position: Python-only and pytest-only for v1; design must not hard-code `pytest` as the only conceivable test command, so the "what runs the tests" hook is per-env even if v1 supports a single value.** See UC5.
6. **Drift guard** (UC4) — built-in feature, or left to a project-authored test? *(genuinely open)*

## Related

- `phase-f-pyve-micromamba-testenv-trap.md` — the motivating case study (the silent-skip trap; `--env main` + advisory already shipped).
- `stories.md` story **F.f.1** — the debug cycle whose prevention scan surfaced all of this.
- `project-essentials.md` "Pyve Essentials" — the repo-context two-env conventions this capability generalizes.
