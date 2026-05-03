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

**`src/learningfoundry/sveltekit_template/` is the source of truth:**
- The generated SvelteKit project in `build/` (or the configured output directory) is a copy produced by `generator.py`. Never edit files in the output directory — always edit `src/learningfoundry/sveltekit_template/` and re-run `learningfoundry build`.
- `curriculum.json` in the output is generated from the resolved curriculum; it does not exist in the template.
- A workspace-root `sveltekit_template/` duplicate existed pre-v0.25.0 and was removed in v0.53.0 (Story I.r) to prevent drift. Do not re-create it; `generator.py` resolves `_TEMPLATE_DIR` from the package-internal path.

**modelfoundry is NOT a direct dependency:**
- `docs/specs/modelfoundry/` contains specs for modelfoundry (the ML training library), but learningfoundry does not import or invoke modelfoundry.
- modelfoundry is consumed internally by nbfoundry. learningfoundry interacts only with nbfoundry's `ExerciseProvider` interface.
- If you see modelfoundry references in older docs, do not wire them into learningfoundry's imports or pipeline.

**Stub providers ship for v1:**
- `NbfoundryStub` and `D3foundryStub` implement the `ExerciseProvider` and `VisualizationProvider` protocols respectively. They return placeholder dicts with `"status": "stub"`.
- The real providers will be added when nbfoundry and d3foundry are published as packages.
- The frontend components detect `status: "stub"` and render placeholder cards.

**In-browser progress DB is per-user-partitioned (Story I.x, v0.58.0):**
- The sql.js database is persisted to IndexedDB under `db:${userId}`, where `userId` is a UUID v4 stored in `localStorage` under `learningfoundry-user-id`.
- Pre-v0.58.0 progress lived under the unkeyed `db` IDB record. The first `Database.getDb()` call for any userId migrates that legacy record to `db:${userId}` and deletes the legacy key. Idempotent.
- Bootstrap is **lazy and self-contained inside the `Database` class**: there is no `bootstrapDb()` ceremony in `+layout.svelte`. The first method call on `progressRepo` triggers the userId resolution and legacy migration. Tests can pass an explicit userId to the constructor (`new Database('user-a')`) for partition-isolation cases.
- The `userId` bootstrap (read-or-create on first visit) is wrapped in `navigator.locks.request('lf-user-id-bootstrap', ...)` so two simultaneously-loading tabs on a fresh browser converge on a single UUID. Browsers without Web Locks (Safari < 15.4) fall back to an unlocked generate-and-store; the race window is small.
- **Auth-migration plan when authentication lands:** swap the `localStorage` UUID for the auth-issued user ID, rename the IDB key once. No schema migration; no per-row `user_id` column. The current architecture treats `userId` as opaque.
- Cross-tab anti-clobber for the *same* `userId` is **not yet solved** — two tabs writing concurrently still last-writer-wins on the IDB blob. Defer until there's evidence of multi-tab learner workflows or sync work makes it forced.

**pnpm node_modules layout — direct vs transitive deps (Story I.cc):**
- pnpm uses a **strict** node_modules layout by default. *Direct* deps declared in `package.json` are symlinked at the top level (`output_dir/node_modules/sql.js → .pnpm/sql.js@<ver>/node_modules/sql.js`); *transitive* deps live only under `.pnpm/<pkg>@<ver>/node_modules/<pkg>/` and are **not** hoisted to the top-level path npm would use.
- The pipeline's [`_ensure_sql_wasm`](../../src/learningfoundry/pipeline.py) reads `output_dir/node_modules/sql.js/dist/sql-wasm.wasm`. This works because `sql.js` is a *direct* dep of [package.json](../../src/learningfoundry/sveltekit_template/package.json#L20). **Verified** in `learningfoundry-test/dist/` against pnpm 10.x and sql.js 1.14.1.
- **Guideline for future pipeline code:** if you ever need to read a *transitive* dep's file, do not hard-code `node_modules/<pkg>/...` — use `find output_dir/node_modules -name '<file>' -print -quit` or have the upstream direct dep re-export the asset. The quizazz README's `find node_modules -name 'sql-wasm*.wasm' -exec cp {} static/ \;` one-liner is the prior-art recipe for this.
- **Side-finding on sql.js@1.14.x:** the package now ships both `sql-wasm.wasm` and `sql-wasm-browser.wasm` (Vite's `"browser"` export condition resolves to the latter). In 1.14.1 the two files are **byte-identical (SHA-256)** — `locateFile: () => '/sql-wasm.wasm'` works regardless of which name Vite resolves at build time. **This is a coincidence, not a contract.** A future sql.js release that genuinely diverges them would resurface the failure mode. See [sql-js-wasm-robustness.md](sql-js-wasm-robustness.md) Pattern A and Pattern C for context.
- Lifecycle scripts (`postinstall`, `prepare`, `prepublish`) are **not** the source of any current bug — Story I.cc was reframed away from a lifecycle-script investigation after the user clarified the actual grief was the strict-layout caveat above (in a separate repo, host-integration scenario).

### Domain Conventions

**Curriculum IDs are hyphenated lowercase strings:**
- Module IDs: `mod-01`, `mod-02`. Lesson IDs: `lesson-01`, `lesson-02`.
- Never integers, never camelCase, never underscored.

**Quiz scores — aggregate only in learningfoundry:**
- quizazz uses a weighted scoring model internally (+1 correct, −2 partially correct, −5 incorrect, −10 ridiculous) and manages per-question detail in its own IndexedDB databases.
- learningfoundry's `quiz_scores` table stores only the aggregate: `score` (points earned) and `max_score` (questions count). Do not attempt to replicate quizazz's per-question schema.

**Progress timestamps are Unix integer seconds:**
- All `completed_at` and `updated_at` columns in the SQLite progress schema are integer Unix timestamps (seconds since epoch), not ISO 8601 strings, not milliseconds.

**Lesson lifecycle is four states, visually three (Story I.p / FR-P15):**
- `lesson_progress.status` runs `not_started → opened → in_progress → complete` (plus the orthogonal `optional`).
- The sidebar visually merges `opened` and `in_progress` into the `…` icon — the data distinction exists for analytics / future hooks, not for direct learner display. Don't add a separate sidebar symbol for `opened`.
- `markLessonOpened` is upgrade-only and never demotes a more advanced status.

### Testing

**Svelte 5 component mounts in vitest require `resolve.conditions: ['browser']` (Story I.q):**
- `vite.config.ts` sets `resolve: process.env.VITEST ? { conditions: ['browser'] } : undefined`. Without the conditions block, vitest pulls Svelte's SSR build and `mount(...)` throws `lifecycle_function_unavailable`.
- Do **not** strip the `process.env.VITEST` guard. Production `vite build` must not pick up the browser conditions or it will mis-bundle SSR-only code paths in the static adapter output.
- Component tests use `@testing-library/svelte`'s `render(...)`. See `mount.test.ts` for the smoke check that the config is wired correctly; if downstream component tests start failing with cryptic `lifecycle_function_unavailable` errors, run `mount.test.ts` first — it fails loudly and obviously when the config silently reverted.

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
