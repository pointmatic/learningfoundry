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
This Project-Guide offers a human-in-the-loop workflow for you to follow that can be dynamically reconfigured based on the project `mode`. Each `mode` defines a focused cycle of steps to guide you (the LLM) to help generate artifacts for some facet in the project lifecycle. This document is customized for code_velocity.

**Approval Gate**
When you have completed the steps, pause for the developer to review, correct, redirect, or ask questions about your work.  

**Rules**
- Work through each step methodically, presenting your work for approval before continuing a cycle. 
- When the developer says "go" (or equivalent like "continue", "next", "proceed"), continue with the next action. 
- If the next action is unclear, tell the developer you don't have a clear direction on what to do next, then suggest something. 
- Never auto-advance past an approval gate—always wait for explicit confirmation. 
- At approval gates, present the completed work and wait. Do **not** propose follow-up actions outside the current mode step — in particular, do not prompt for git operations (commits, pushes, PRs, branch creation), CI runs, or deploys unless the current step explicitly calls for them. The developer initiates these on their own schedule.
- After compacting memory, re-read this guide to refresh your context.

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
- `pyve run` guarantees the command executes within the project's virtual environment at the project root. This eliminates the need for editable installs (`pip install -e .`) — do not use them.
- Never use bare `python ...` or `.venv/bin/python ...` — both bypass pyve's guarantees and may resolve to a different Python on `$PATH`.

**Dev tool installation — use `pyve testenv`:**
- Dev/test tools (pytest, ruff, mypy) live in an isolated testenv, not the project venv.
- Setup: `pyve testenv --init`, then `pyve testenv --install -r requirements-dev.txt`.
- Run dev tools via: `pyve testenv run ruff check .`, `pyve testenv run mypy src/`.
- Do not `pip install ruff mypy` into the project venv — that pollutes the runtime dependency graph.

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


---

# code_velocity mode (cycle)

> Generate code with velocity


Implement stories rapidly with direct commits to main. Focus on feature completion and iteration speed over process overhead.

**Next Action**
Restart the cycle of steps. 

---


## Cycle Steps

For each story:

1. **Read** the story's checklist from `docs/specs/stories.md`
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

