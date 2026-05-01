# Project-Guide — Calm the chaos of LLM-assisted coding

This document provides step-by-step instructions for an LLM to assist a human developer in a project. 

## How to Use Project-Guide

### For Developers
After installing project-guide (`pip install project-guide`) and running `project-guide init`, instruct your LLM as follows in the chat interface: 

```
Read `docs/project-guide/go.md`
```

After reading, the LLM will respond:
1. (optional) "I need more information..." followed by a list of questions or details needed. 
  - LLM will continue asking until all needed information is clear.
2. "The next step is ___."
3. "Say 'go' when you're ready." 

For efficiency, when you change modes, start a new LLM conversation. 

### For LLMs

**Modes**
This Project-Guide offers a human-in-the-loop workflow for you to follow that can be dynamically reconfigured based on the project `mode`. Each `mode` defines a focused cycle of steps to guide you (the LLM) to help generate artifacts for some facet in the project lifecycle. This document is customized for code_direct.

**Approval Gate**
When you have completed the steps, pause for the developer to review, correct, redirect, or ask questions about your work.  

**Rules**
- Work through each step methodically, presenting your work for approval before continuing a cycle. 
- When the developer says "go" (or equivalent like "continue", "next", "proceed"), continue with the next action. 
- If the next action is unclear, tell the developer you don't have a clear direction on what to do next, then suggest something. 
- Never auto-advance past an approval gate—always wait for explicit confirmation. 
- At approval gates, present the completed work and wait. Do **not** propose follow-up actions outside the current mode step — in particular, do not prompt for git operations (commits, pushes, PRs, branch creation), CI runs, or deploys unless the current step explicitly calls for them. The developer initiates these on their own schedule.
- After compacting memory, re-read this guide to refresh your context.
- Before recording a new memory, reflect: is this fact project-specific (belongs in `docs/specs/project-essentials.md`) or cross-project (belongs in LLM memory)? Could it belong in both? If project-specific, add it to `project-essentials.md` instead of or in addition to memory.
- When creating any new source file, add a copyright notice and license header using the comment syntax for that file type (`#` for Python/YAML/shell, `//` for JS/TS, `<!-- -->` for HTML/Svelte). Check this project's `project-essentials.md` for the specific copyright holder, license, and SPDX identifier to use.

---

## Project Essentials

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



### Pyve Essentials

#### Workflow rules — pyve environment conventions

This project uses `pyve` with **two separate environments**. Picking the wrong invocation form often "works" but leads to subtle drift. Use the canonical forms below:

- **Runtime code (the package itself):** `pyve run python ...` or `pyve run <entry-point> ...`.
- **Tests:** `pyve test [pytest args]` — **not** `pyve run pytest`. Pytest is not installed in the main `.venv/`; it lives in the dev testenv at `.pyve/testenv/venv/`.
- **Dev tools (ruff, mypy, pytest):** `pyve testenv run ruff check ...`, `pyve testenv run mypy ...`.
- **Install dev tools:** `pyve testenv --install -r requirements-dev.txt`. **Do not** run `pip install -e ".[dev]"` into the main venv — that pollutes the runtime environment with test-only dependencies and breaks the two-env isolation.

If `pytest` fails with "not found" that is the signal to use `pyve test`, not to `pip install pytest` into the wrong venv.

#### LLM-internal vs. developer-facing invocation

`pyve run` is for the LLM's own Bash-tool invocations; developer-facing command suggestions use the bare form verbatim from the mode template.

- ✅ Developer-facing: `project-guide mode plan_phase`
- ❌ Developer-facing: `pyve run project-guide mode plan_phase`
- ✅ LLM Bash-tool: `pyve run project-guide mode plan_phase`

**Why:** the LLM's Bash-tool shell does not auto-activate `.venv/`, so the LLM must wrap its own commands with `pyve run`. The developer's shell is typically already pyve/direnv-activated, so the bare form resolves correctly and matches the commands quoted throughout mode templates and documentation.

**How to apply:** never prepend environment wrappers (`pyve run`, `poetry run`, `uv run`, etc.) to commands you quote back to the developer from a mode template. Use the wrapper only when you execute the command yourself through the Bash tool.

#### Python invocation rule

Always use `python`, never `python3`. The `python3` command bypasses `asdf` version shims and may resolve to the system interpreter rather than the project-pinned version, leading to subtle version mismatches.

#### `requirements-dev.txt` story-writing rule

Any story that introduces dev tooling (ruff, mypy, pytest, types-* stubs) **must** include a task to create or update `requirements-dev.txt` so that `pyve testenv --install -r requirements-dev.txt` reproduces the full dev environment in one step. This keeps the dev environment reproducible and prevents "it works on my machine" drift.

#### Editable install and testenv dependency management

LLMs often get confused about *where* to install an editable package when using pyve's two-environment model. The wrong choice "works" but creates subtle drift.

**Main environment only (preferred for library projects):**
```bash
pyve run pip install -e .
```
Then configure pytest to find the source tree without a second editable install:
```toml
# pyproject.toml
[tool.pytest.ini_options]
pythonpath = ["."]   # or ["src"] for src layout
```
`pythonpath` handles import discovery cleanly and avoids maintaining two editable installs with potentially diverging dependency resolution.

**Testenv editable install (required for CLI projects):**
```bash
pyve testenv run pip install -e .
pyve testenv --install -r requirements-dev.txt
```
Use this when tests invoke CLI entry points (console scripts), because `pythonpath` only handles imports — it does not register entry points.

**Rule of thumb:** use `pythonpath` for library/package projects; use editable install in testenv for projects whose tests exercise CLI entry points.

**Important:** When `pyve` purges and reinitialises the main environment, the testenv remains intact and the testenv editable install survives. Re-running `pyve run pip install -e .` restores the main-environment editable install. See `developer/python-editable-install.md` for the full decision guide.


---

# code_direct mode (cycle)

> Generate code directly, test after


Implement stories rapidly with direct commits to main. Focus on feature completion and iteration speed over process overhead.

**Next Action**
Restart the cycle of steps. 

---


## Cycle Steps

For each story:

1. **Read** the story's checklist from `docs/specs/stories.md` — always re-fetch from disk with the `Read` tool at the start of each cycle. The developer may have edited the file since you last viewed it (added tasks, reworded scope, marked items done), so do not rely on prior conversation context for its contents.
2. **Implement** all tasks in the checklist
3. **Add copyright/license headers** to every new source file
4. **Run tests** -- `pyve run pytest` (fix failures before continuing)
5. **Run linting** -- fix any issues immediately
6. **Mark tasks** as `[x]` in `stories.md` and change story suffix to `[Done]`
7. **Bump version** in package manifest and source (if the story has a version)
8. **Update CHANGELOG.md** with the version entry
9. **Present** the completed story concisely: what changed (files + line refs), verification results (test counts, lint status), and the suggested next story. Do not propose commits, pushes, or bundling options. Do not offer "want me to also…?" follow-ups.
10. **Wait** for the developer to say "go" before starting the next story

## Velocity Practices

**LLM's role in each cycle:**

- **Version bump per story** -- v0.1.0, v0.2.0, v0.3.0, etc. — bump in package manifest and source
- **Minimal process overhead** -- focus on making it work, not making it perfect
- **Tests run after every story** -- not after every file, but before presenting to developer
- **Fix linting immediately** -- small incremental fixes, not batch cleanup
- **Update CHANGELOG.md** with the version entry before presenting

**Developer's role (do NOT prompt for, offer, or initiate):**

- **Direct commits to main** -- no branches, no PRs, no code review (velocity convention)
- **Commit messages** reference story IDs: `"Story A.a: v0.1.0 Hello World"`
- **Decides when to commit** -- the LLM presents, the developer commits. Multiple stories may be bundled into one commit at the developer's discretion — that is not the LLM's call to make or suggest.

## Story Ordering

- Start with Story A.a (Hello World) if not yet implemented
- If unclear which story is next, ask: "Which story should I work on next?"
- Never skip ahead -- complete stories in order within each phase

## File Header Reminder

Every new source file must include the copyright and license header as the very first content (before code, docstrings, or imports).

## When to Switch Modes

Switch to **code_test_first** when:
- Working on a story with complex logic that benefits from TDD
- The developer requests test-first approach

Switch to **debug** when:
- A bug is discovered during implementation
- Tests are failing unexpectedly

Switch to **production mode** when:
- CI/CD phase is complete and branch protection is enabled
- The project is ready for public users

