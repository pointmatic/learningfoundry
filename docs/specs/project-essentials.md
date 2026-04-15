<!--
This file captures must-know facts future LLMs need to avoid blunders when
working on this project. Anything a smart newcomer could miss on day one and
waste time on goes here.

This content gets injected verbatim under a `## Project Essentials` section
in every rendered `go.md`, so entries below should use `###` for subsections
(not `##`, which would collide with the wrapper heading). Do NOT include a
top-level `#` title — the wrapper provides it.
-->

### Workflow Rules — pyve and Environment Conventions

**Python invocation — use `pyve run`:**
- Canonical form: `pyve run python script.py`, `pyve run python -m learningfoundry ...`
- `pyve run` guarantees the command executes within the project's virtual environment at the project root. Do not use editable installs (`pip install -e .`) in the main project venv.
- Never use bare `python ...` or `.venv/bin/python ...` — both bypass pyve's guarantees and may resolve to a different Python on `$PATH`.

**Dev tool installation — use `pyve testenv`:**
- Dev/test tools (pytest, ruff, mypy) live in an isolated testenv, not the project venv.
- Setup: `pyve testenv --init`, then `pyve testenv --install -r requirements-dev.txt`.
- Run dev tools via: `pyve testenv run ruff check .`, `pyve testenv run mypy src/`.
- Do not `pip install ruff mypy` into the project venv — that pollutes the runtime dependency graph.

**Testenv editable install — required for tests to import the package:**
- The testenv does not automatically see the project source. Bootstrap it once with: `pyve testenv run pip install -e .`
- This is safe and correct — editable installs in the testenv are expected; it is only the main project venv where they are avoided.
- `pyve testenv --install` only accepts a requirements file (`-r`), not raw pip arguments — use `pyve testenv run pip install ...` for one-off installs.

**Test invocation — use `pyve test`:**
- Canonical form: `pyve test`, `pyve test tests/test_parser.py -v`, `pyve test -k test_resolve`.
- `pyve test` dispatches to the testenv and auto-installs pytest if needed.
- Do not use bare `pytest` — it may not be installed in the active venv, and the failure is a signal to use `pyve test`, not to `pip install pytest`.

**Node/pnpm — used directly:**
- pyve is a Python environment manager and does not wrap Node.js tooling.
- Use bare `pnpm install`, `pnpm build`, `pnpm dev` for the SvelteKit frontend.

### Architecture Quirks

**`sveltekit_template/` is the source of truth:**
- The generated SvelteKit project in `build/` (or the configured output directory) is a copy produced by `generator.py`. Never edit files in the output directory — always edit `sveltekit_template/` and re-run `learningfoundry build`.
- `curriculum.json` in the output is generated from the resolved curriculum; it does not exist in the template.

**modelfoundry is NOT a direct dependency:**
- `docs/specs/modelfoundry/` contains specs for modelfoundry (the ML training library), but learningfoundry does not import or invoke modelfoundry.
- modelfoundry is consumed internally by nbfoundry. learningfoundry interacts only with nbfoundry's `ExerciseProvider` interface.
- If you see modelfoundry references in older docs, do not wire them into learningfoundry's imports or pipeline.

**Stub providers ship for v1:**
- `NbfoundryStub` and `D3foundryStub` implement the `ExerciseProvider` and `VisualizationProvider` protocols respectively. They return placeholder dicts with `"status": "stub"`.
- The real providers will be added when nbfoundry and d3foundry are published as packages.
- The frontend components detect `status: "stub"` and render placeholder cards.

### Domain Conventions

**Curriculum IDs are hyphenated lowercase strings:**
- Module IDs: `mod-01`, `mod-02`. Lesson IDs: `lesson-01`, `lesson-02`.
- Never integers, never camelCase, never underscored.

**Quiz scores — aggregate only in learningfoundry:**
- quizazz uses a weighted scoring model internally (+1 correct, −2 partially correct, −5 incorrect, −10 ridiculous) and manages per-question detail in its own IndexedDB databases.
- learningfoundry's `quiz_scores` table stores only the aggregate: `score` (points earned) and `max_score` (questions count). Do not attempt to replicate quizazz's per-question schema.

**Progress timestamps are Unix integer seconds:**
- All `completed_at` and `updated_at` columns in the SQLite progress schema are integer Unix timestamps (seconds since epoch), not ISO 8601 strings, not milliseconds.

### Hidden Coupling

**Provider protocols ↔ dependency specs:**
- `QuizProvider`, `ExerciseProvider`, and `VisualizationProvider` in `integrations/protocols.py` define the Python-side contracts.
- These must stay in sync with the API contracts in `docs/specs/quizazz/dependency-spec.md`, `docs/specs/nbfoundry/dependency-spec.md`, and `docs/specs/d3foundry/dependency-spec.md`.
- If you change a provider method signature, update both the protocol and the corresponding dependency spec.

**TypeScript interfaces ↔ Python dict schemas:**
- `ExerciseContent`, `VisualizationContent`, `QuizManifest` in `lib/types/index.ts` describe the JSON shape of dicts returned by the Python providers.
- Changes to a provider's return dict (e.g., adding a field to `compile_exercise`'s output) must be reflected in the corresponding TypeScript interface.

**Curriculum YAML schema ↔ Pydantic models ↔ TypeScript types:**
- The YAML content block types (`text`, `video`, `quiz`, `exercise`, `visualization`) are defined in three places: the YAML schema docs, the Pydantic `ContentBlock` union in `schema_v1.py`, and the `ContentBlock` TypeScript interface. Adding a new block type requires updating all three.
