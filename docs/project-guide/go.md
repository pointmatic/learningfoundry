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
This Project-Guide offers a human-in-the-loop workflow for you to follow that can be dynamically reconfigured based on the project `mode`. Each `mode` defines a focused cycle of steps to guide you (the LLM) to help generate artifacts for some facet in the project lifecycle. This document is customized for debug.

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

# debug mode (cycle)

> Debug code with a test-first approach


This mode is a structured approach for LLMs to help developers debug issues in existing software projects. It emphasizes test-driven debugging, root cause analysis, and preventing regressions.

**Next Action**
Restart the cycle of steps. 

---


## Core Debugging Principles

### 1. Test First, Fix Second

**Always write a failing test before attempting a fix.**

**Why:**
- A test provides a concrete, reproducible demonstration of the bug
- It gives you a clear "exit condition" (test passes = bug fixed)
- It prevents "oops...not fixed yet" cycles where you think you've fixed it but haven't
- It serves as regression protection for the future
- It forces you to understand the bug well enough to codify it

**Process:**
1. Read the bug report or error message
2. Write a minimal test case that demonstrates the failure
3. Run the test to confirm it fails
4. Implement the fix
5. Run the test to confirm it passes
6. Run the full test suite to ensure no regressions

**Example:**

❌ **What NOT to do:**
```
User: "The data processor is producing duplicate IDs"
LLM: "Let me fix the ID generation function..." [makes changes]
LLM: "Let me test with the real data file..." [processes file]
LLM: "Hmm, still not working, let me try a different approach..."
```

✅ **What TO do:**
```
User: "The data processor is producing duplicate IDs"
LLM: "Let me write a test that demonstrates this bug..."
[Writes test_id_generator_with_multiple_sources()]
LLM: "Test fails as expected. Now implementing fix..."
[Implements fix]
LLM: "Test passes. Running full suite to check for regressions..."
```

### 2. Understand Before Acting

**Analyze the root cause before proposing solutions.**

**Questions to ask:**
- What is the expected behavior?
- What is the actual behavior?
- Where in the codebase does this behavior originate?
- Why wasn't this caught by existing tests?
- Is this a requirements gap, implementation bug, or test coverage gap?

### 3. Prefer Unit Tests Over Integration Tests for Debugging

**Use the smallest possible test scope.**

**Why:**
- Unit tests are faster to run
- Unit tests are easier to debug (fewer moving parts)
- Unit tests pinpoint the exact function/module with the bug
- Integration tests are valuable but unstable for debugging

**Test Hierarchy:**
1. **Unit test** - Test a single function in isolation (preferred for debugging)
2. **Integration test** - Test multiple components together
3. **End-to-end test** - Test the full pipeline (useful for verification, not debugging)

**Example:**
- ❌ Testing ID generation by processing a full data file with thousands of records
- ✅ Testing ID generation with a minimal list of 8 test objects

---

## Structured Debugging Workflow

### Step 1: Reproduce the Bug

**Goal:** Create a minimal, reliable reproduction of the issue.

**Actions:**
1. Read the bug report carefully
2. Identify the symptoms (error message, incorrect output, unexpected behavior)
3. Determine the input that triggers the bug
4. Create a minimal test case that reproduces the bug

**Output:** A failing test that demonstrates the bug

### Step 2: Analyze Root Cause

**Goal:** Understand why the bug exists.

**Questions to investigate:**

#### A. Requirements Analysis
- Is the expected behavior clearly defined in `features.md`?
- Is the implementation approach specified in `tech_spec.md`?
- Is there ambiguity in the requirements?
- Was this requirement overlooked during initial design?

#### B. Implementation Analysis
- Which function/module contains the bug?
- What assumptions did the code make that are incorrect?
- Are there edge cases that weren't considered?
- Is the algorithm fundamentally flawed or just missing a check?

#### C. Test Coverage Analysis
- Why didn't existing tests catch this?
- Is there a gap in test coverage?
- Are the tests testing the wrong thing?
- Are the tests too high-level (integration) vs. unit tests?

**Output:** A clear understanding of:
1. What went wrong
2. Where it went wrong
3. Why it went wrong
4. Why tests didn't catch it

### Step 3: Design the Fix

**Goal:** Plan a minimal, targeted fix.

**Considerations:**
- What's the smallest change that fixes the root cause?
- Does this fix introduce new edge cases?
- Does this fix require changes to the public API?
- Will this fix break existing functionality?

**Approaches:**
1. **Fix the implementation** - Bug in the code logic
2. **Add validation** - Missing input validation or error checking
3. **Refactor** - Fundamental design flaw requiring restructuring
4. **Update requirements** - Behavior is actually correct, requirements were wrong

**Output:** A clear plan for the fix

### Step 4: Implement the Fix

**Goal:** Make the minimal change to fix the bug.

**Process:**
1. Implement the fix
2. Run the failing test - it should now pass
3. Run the full test suite - no regressions
4. Add additional tests for edge cases if needed

**Output:** Working code with passing tests — but the cycle is not complete; proceed to Step 5.

### Step 5: Document the Fix in `stories.md` (Approval Gate)

**Goal:** Make the fix legible to future debuggers and prevent this class of bug from recurring.

This step has **two distinct artifacts**. (a) is the gate; (b) is required but secondary.

**(a) The story write-up — the gate artifact:**

Create a new story in `docs/specs/stories.md` matching the project format (see the bundled `stories.md` template and `project-essentials.md` for commit/version conventions). Implementation tasks the fix actually completed are marked `[x]`; any housekeeping tasks discovered during the fix (related-bug scans, doc updates) are marked `[ ]` and left for follow-up.

**(b) The prevention scan — required, but separate from the gate:**

1. Update `features.md` or `tech-spec.md` if the requirements were ambiguous.
2. Add test coverage for the bug scenario (if not already added in Step 4).
3. Look elsewhere in the codebase for similar bugs — the same root cause pattern often appears in more than one place. Either fix any matches inline (mark `[x]`) or capture them as `[ ]` housekeeping in the story for follow-up.

**Output:** A story in `docs/specs/stories.md` matching the project format. **Until this story exists, the cycle is not complete** — Step 4 produces working code, Step 5 produces a complete project record.

---

**The approval gate is not reached until all five steps have produced their named output artifact. If you cannot name the Step 5 artifact (the new story in `stories.md`), you are not at the gate.**

---

## Debugging Checklist

**Before pausing for approval, run this checklist and confirm each item.** This is a mandatory pre-gate run-through, not a reference.

- [ ] I have written a test that demonstrates the bug
- [ ] The test fails before the fix
- [ ] I understand the root cause (requirements, implementation, or test gap)
- [ ] I have designed a minimal fix
- [ ] The fix addresses the root cause, not just symptoms
- [ ] The test passes after the fix
- [ ] All existing tests still pass (no regressions)
- [ ] I have added additional tests for edge cases if needed
- [ ] I have documented the fix in `stories.md` (created a new story) — **the Step 5 gate artifact**
- [ ] I have updated `features.md` or `tech-spec.md` if requirements were ambiguous
- [ ] I have looked elsewhere in the codebase for similar bugs (fixed inline or captured as `[ ]` housekeeping)

---

## Root Cause Analysis Framework

### Requirements Gap Analysis

**Check `features.md` for:**
- [ ] Is the expected behavior explicitly defined?
- [ ] Are edge cases documented?
- [ ] Are constraints clearly stated?
- [ ] Are validation rules specified?

**Check `tech_spec.md` for:**
- [ ] Is the implementation approach clear?
- [ ] Are data structures well-defined?
- [ ] Are algorithms specified?
- [ ] Are module responsibilities clear?

**Common requirements gaps:**
- Implicit assumptions not documented
- Edge cases not considered
- Ambiguous language ("should", "may", "usually")
- Missing validation rules
- Incomplete acceptance criteria

### Test Coverage Gap Analysis

**Questions:**
- [ ] Do unit tests exist for this function?
- [ ] Do tests cover edge cases?
- [ ] Do tests cover error conditions?
- [ ] Are tests testing implementation details or behavior?
- [ ] Are integration tests masking unit test gaps?

**Common test gaps:**
- High-level integration tests without unit tests
- Happy path testing only (no edge cases)
- Testing implementation details instead of behavior
- Missing negative test cases (error conditions)
- Insufficient boundary testing

### Implementation Bug Analysis

**Questions:**
- [ ] Is the algorithm correct?
- [ ] Are there off-by-one errors?
- [ ] Are there race conditions or ordering issues?
- [ ] Are assumptions about input data incorrect?
- [ ] Are there type mismatches or conversion errors?

**Common implementation bugs:**
- Incorrect loop bounds
- Wrong comparison operators
- Missing null/empty checks
- Incorrect data structure usage
- Side effects from shared state

---

## Case Study: Duplicate ID Generation Bug

### The Bug

**Context:** A data processing system generates unique IDs for records. The system has two data sources: initial state (loaded from a snapshot) and new transactions (from an event stream). Both sources feed into a combined output.

**Symptom:** Record IDs were duplicated when initial state and new transactions occurred on the same date (e.g., `REC-2023-01-01-0001` appeared 6 times instead of being split into separate records).

**Impact:** Violated uniqueness constraint, compromised data integrity, made output unusable for downstream systems.

### Root Cause Analysis

#### 1. Requirements Gap?

**Requirements stated:**
```
Generate unique record IDs:
- Format: REC-YYYY-MM-DD-NNNN
- YYYY-MM-DD: record date
- NNNN: sequential number starting at 0001 for each date
- All entries for a single record share the same ID
- IDs are numbered in the order they appear in the output
```

**Analysis:**
- ✅ Requirement states "unique record IDs"
- ✅ Requirement states "sequential number starting at 0001 for each date"
- ❌ **GAP:** Requirement doesn't specify what happens when initial state and transactions are combined
- ❌ **GAP:** Phrase "All entries for a single record share the same ID" is ambiguous when combining data sources
- ❌ **GAP:** No explicit requirement that each record must have a globally unique ID across all sources

**Verdict:** **Partial requirements gap** - The requirement was present but not explicit enough about the combination scenario.

#### 2. Test Coverage Gap?

**Existing tests:**
- ✅ Tests for `load_initial_state()` in isolation
- ✅ Tests for `process_transactions()` in isolation
- ❌ **GAP:** No tests for combining initial state and transactions on the same date
- ❌ **GAP:** No tests validating ID uniqueness across the full output
- ❌ **GAP:** Integration tests used real data but didn't assert on ID uniqueness

**Verdict:** **Critical test coverage gap** - The specific scenario (initial state + transactions on same date) was never tested.

#### 3. Implementation Bug?

**Code analysis:**
```python
# In processor.py
initial_records = load_initial_state(...)  # IDs start at 0001
new_records = process_transactions(...)     # IDs also start at 0001
all_records.extend(initial_records)
all_records.extend(new_records)
all_records.sort(key=lambda r: (r.date, r.id))  # Sort interleaves duplicates
```

**Analysis:**
- ❌ Both functions independently assign IDs starting at 0001
- ❌ No coordination between the two ID generation schemes
- ❌ Sort interleaves records with duplicate IDs, creating ID collisions

**Verdict:** **Implementation bug** - The code didn't account for combining records from two sources.

### Why Wasn't This Caught Earlier?

**Three contributing factors:**

1. **Requirements ambiguity** - The requirement for "unique IDs" existed but didn't explicitly address the combination scenario.

2. **Test coverage gap** - No unit test verified ID uniqueness when combining initial state and transactions. Integration tests existed but didn't assert on this property.

3. **Test-last approach** - The initial fix attempt was made without first writing a test, leading to a "not fixed yet" cycle. Only after writing `test_id_generation_with_multiple_sources()` was the bug properly fixed.

### Lessons Learned

1. **Write tests for integration points** - When combining outputs from two functions, test the combined result, not just each function in isolation.

2. **Test invariants explicitly** - "IDs must be unique" is an invariant that should be tested explicitly, not assumed.

3. **Test first, always** - Writing the test first would have:
   - Demonstrated the bug clearly
   - Provided a concrete exit condition
   - Prevented the "try fix, check manually, still broken" cycle

4. **Unit tests > Integration tests for debugging** - The end-to-end test with real data files was unstable and slow. The focused unit test with minimal test objects was stable and precise.

5. **Clarify requirements proactively** - When implementing features that combine multiple components, explicitly document how they interact.

---

## Common Debugging Scenarios

### Scenario 1: "It works in tests but fails in production"

**Root cause:** Test data doesn't match production data characteristics

**Debugging steps:**
1. Capture the production input that fails
2. Create a test case with that exact input
3. Verify the test fails
4. Fix the bug
5. Verify the test passes
6. Add similar test cases for related edge cases

### Scenario 2: "Tests pass but the feature doesn't work"

**Root cause:** Tests are testing the wrong thing or testing implementation details

**Debugging steps:**
1. Review what the tests actually assert
2. Verify tests are testing behavior, not implementation
3. Add tests that verify the actual user-facing behavior
4. Fix the implementation to match requirements
5. Ensure tests now verify the correct behavior

### Scenario 3: "Fixing one bug breaks something else"

**Root cause:** Insufficient test coverage or tight coupling

**Debugging steps:**
1. Identify what broke (which tests failed)
2. Understand why the fix caused the breakage
3. Determine if the original fix was correct
4. Either:
   - Adjust the fix to not break existing functionality
   - Update the broken tests if they were testing incorrect behavior
5. Add tests to prevent this regression

### Scenario 4: "Can't reproduce the bug"

**Root cause:** Missing context about the environment or input

**Debugging steps:**
1. Ask user for exact input data, command line, environment
2. Ask user for exact error message or incorrect output
3. Try to reproduce with minimal test case
4. If still can't reproduce, ask user to run with verbose logging
5. Use logging output to understand what's different

---

## Anti-Patterns to Avoid

### ❌ Fix First, Test Later

**Problem:** You think you've fixed it, but you haven't. No concrete exit condition.

**Solution:** Always write the failing test first.

### ❌ Testing with Real Data Only

**Problem:** Real data is complex, slow, and hard to debug. "Wildly unstable."

**Solution:** Create minimal unit tests with synthetic data.

### ❌ Fixing Symptoms Instead of Root Cause

**Problem:** Bug will resurface in a different form.

**Solution:** Analyze why the bug exists, not just what the bug is.

### ❌ Skipping Root Cause Analysis

**Problem:** You don't learn from the bug, similar bugs will occur.

**Solution:** Always ask "why wasn't this caught earlier?"

### ❌ Over-Engineering the Fix

**Problem:** Introduces complexity, new bugs, or breaks existing functionality.

**Solution:** Make the minimal change that fixes the root cause.

### ❌ Not Updating Requirements

**Problem:** Ambiguous requirements lead to more bugs.

**Solution:** If requirements were unclear, update them as part of the fix.

### ❌ Declaring the Fix Complete After Step 4

**Problem:** Step 4 is "code works"; Step 5 is "cycle is done." Skipping Step 5 leaves the project record incomplete and the next debugger blind to what was learned. The 5-step workflow has a single named output artifact for each step — Step 5's artifact is the new story in `stories.md`. Without it, there is no gate.

**Solution:** Run the Debugging Checklist before declaring the cycle complete. If you cannot point to a story in `stories.md` documenting this fix, you are at Step 4, not at the gate.

---

## When to Escalate to User

**Escalate when:**
- Requirements are fundamentally ambiguous and you need user clarification
- Multiple valid interpretations exist for expected behavior
- Fix would require breaking changes to public API
- Fix would require significant refactoring
- You've tried multiple approaches and tests still fail

**Don't escalate when:**
- You haven't written a test yet
- You haven't analyzed the root cause
- You haven't tried the obvious fix
- You're just stuck on implementation details

---

## Summary

**The Golden Rule of Debugging:**

> **Write a failing test first. Fix the code second. Verify the test passes third. Document the fix in `stories.md` fourth.**

This simple rule prevents:
- "Oops, not fixed yet" cycles
- Regressions
- Unclear exit conditions
- Wasted time on manual testing

**The Three Questions:**

1. **Why did this bug exist?** (Requirements gap, implementation bug, or both?)
2. **Why didn't tests catch it?** (Test coverage gap, wrong test level, or testing wrong thing?)
3. **How do we prevent this class of bug?** (Update requirements, add tests, refactor?)

**The Test Hierarchy:**

1. **Unit tests** - Fast, focused, stable (use for debugging)
2. **Integration tests** - Medium scope, useful for verification
3. **End-to-end tests** - Slow, complex, unstable (use for final validation only)

Follow this guide to debug systematically, learn from bugs, and prevent regressions.

