# pyve-framework-plugin-architecture.md — Pyve as a framework home-base with first-class ecosystem plugins

**Status:** Context brief / strategic-direction prompt for **pyve** maintainers (drafted 2026-05-28 from a learningfoundry-side review). **Not** a design or implementation spec — pyve owns the design and the charter decision. This doc supplies the problem framing, the worked example, the plugin contract sketch, and the open questions, so pyve can decide whether to evolve from "Python virtual environment manager" into "project environment orchestrator with first-class plugins for other ecosystems."

**Audience:** pyve maintainers (strategic input — a charter-level question, not a feature ask).

**Relationship to other briefs:**
- [pyve-named-testenvs.md](pyve-named-testenvs.md) is the *tactical* doc — named test environments within the current Python-only charter. **UC5 in that doc punts polyglot to "out of scope for v1, must not preclude."** This doc is where that punt's eventual answer lives.
- The two should land in this order: (a) named-testenvs ships under the current charter, (b) this doc's charter question is decided, (c) if approved, plugin architecture is designed in a way that *consumes* the named-env primitive (env types become a contribution surface), not the other way around.

---

## The reframing in one paragraph

Today, [`concept.md`](pyve/concept.md) defines pyve as "Pyve: Python Virtual Environment Manager." Its out-of-scope list explicitly names "Docker container or cloud environment management" but is silent on other-language ecosystems because they were never in view. The reframing under consideration: **pyve grows from "Python virtualenv manager" into a project environment orchestrator with a plugin contract — and the Python ecosystem is itself implemented as the first, default, always-shipped plugin.** Other ecosystems (SvelteKit/Node, Go, Rust, Docker, TypeScript, Swift, Kotlin, …) plug in via the same contract. The metaphor: *green-card residents are indistinguishable from citizens in terms of integration capability* — origin marks history, not status. Full participation in `init`, `purge`, `check`, `status`, `run`, `test`, the `.env` lifecycle, the self-healing `.gitignore`, and the activation model is the contract every plugin satisfies, Python included.

## Carrier audience — who brings pyve into a polyglot project

Pyve's home audience is the Python community, and that is its distribution vector. A Rust developer will not discover pyve first; a **Python developer dabbling in Rust** will carry pyve into a Rust project. Same for Node, Svelte, Docker, Swift, Kotlin, TypeScript. Design accordingly: the polyglot story is "Python devs reaching into other ecosystems and bringing their tooling discipline with them," not "polyglot devs choosing pyve cold."

This framing makes the design defensible in two ways. First, pyve is not pretending to be ecosystem-neutral by origin — it is Python-rooted *and* polyglot-capable, and the rooting is honest. Second, the "Python plugin first, others second" implementation order matches the distribution order: the people most likely to file the first bugs against the SvelteKit plugin are Python developers whose Python plugin works fine, not SvelteKit-only developers who would expect a Node-native tool. Optimize for the actual user, not a hypothetical neutral one.

**Implication for the project name.** Keep "Pyve." It has staying power, it has home-audience recognition, and its Python-rooted connotation is a *feature* — it signals the design philosophy is grounded in Python-community discipline, which is precisely what Python developers carry into other ecosystems. No rename, no sub-brand. The tagline shifts to reflect the broader capability ("Pyve — project environments, Python-rooted, polyglot-capable" or similar).

## Why this is being floated (the motivating pain)

The trigger is real polyglot pain that the existing charter declines to address. Concretely (learningfoundry as the worked case):

- A SvelteKit frontend lives at [`src/learningfoundry/sveltekit_template/`](../../src/learningfoundry/sveltekit_template/) alongside a Python codegen package.
- The Python tests include a `@pytest.mark.smoke` test that shells out to `pnpm install` + `vite build` to validate the bundled template — a Python test orchestrating a Node toolchain.
- Activation today: direnv handles Python; Node tooling is provisioned by the host shell or asdf-node; there is no single "activate this project" verb.
- Diagnostics today: `pyve check` reports on the Python env; `node --version` / `pnpm --version` / `package.json` freshness must be checked separately and remembered separately.
- Secrets today: one `.env` shared. The Python side respects `chmod 600`; the Node side has its own assumptions about `.env*` files (Vite's `.env.local`, etc.) that the pyve-managed `.gitignore` doesn't know about.

The pain is **not** "I need pyve to be a Node package manager." It's: *the orchestration discipline pyve provides for Python — one entry point, secure defaults, self-healing config, smart purge, health diagnostics — has no peer for the Node side, and the lack of a peer means the Python-side discipline is silently weaker than it appears.*

The named-testenvs doc handles a narrow slice of this (test environments). A plugin architecture would handle the whole charter.

## What "first-class plugin" means concretely

This is the load-bearing definition. A plugin earns its green card by satisfying a contract that mirrors what the Python core already provides. Sketch:

1. **Config namespace.** A reserved top-level key in [`.pyve/config`](pyve/README.md) (e.g., `sveltekit:` alongside `venv:` / `micromamba:` / `python:`). The plugin reads its own block; pyve core does not interpret it.
2. **Backend declaration.** Plugin registers one or more backends. `pyve init --backend node-pnpm` becomes valid because the SvelteKit plugin declared `node-pnpm`.
3. **Auto-detection participation.** Plugin contributes a detection rule (e.g., "match if `package.json` ∧ (`svelte.config.js` ∨ vite config references @sveltejs/kit)"). The existing precedence chain ([features.md FR-8](pyve/features.md)) extends to include plugin votes.
4. **Lifecycle hooks.** Plugin implements a subset of `init`, `purge`, `update`, `check`, `status`, `run`, `test`. Not every hook is required; missing hooks are no-ops, not errors. Hooks receive a typed context (project root, config block, requested verbosity) and return a typed result (status rows, exit-code contribution).
5. **Activation model contribution.** Plugin owns the answer to "what does direnv do for this ecosystem?" For SvelteKit: PATH munging to put pnpm-managed binaries first, NODE_OPTIONS pinning, etc. The plugin emits its activation snippet; pyve composes plugin snippets into the single `.envrc` it manages.
6. **Diagnostics contribution.** Plugin contributes rows to `pyve check` (with severity using the existing pass/warn/error ladder from [tech-spec.md](pyve/tech-spec.md)) and `pyve status` (read-only state).
7. **Self-healing `.gitignore` participation.** Plugin contributes ecosystem-specific entries to the Pyve-managed template section ([features.md "Self-healing .gitignore"](pyve/features.md)). Core preserves user entries below the template; plugin entries live *inside* the template, scoped to the plugin's section.
8. **Smart-purge contribution.** Plugin declares what it created (and may delete) vs. what is user-authored (and must be preserved). Mirrors the existing `.env` non-empty rule.

Plugins **do not** get:
- The right to bypass cloud-sync refusal (universal, core-owned).
- The right to weaken `.env` permissions or skip `.gitignore` self-healing.
- The right to install pyve itself or modify `~/.local/.env`.
- The right to add commands outside the existing verb set (they extend `--backend`, `--env`, hook into existing commands; they don't add new top-level verbs).

## SvelteKit as the worked example

Concrete walk-through of what the SvelteKit plugin would do, anchored in learningfoundry's actual surface:

| Hook | SvelteKit plugin behavior |
|---|---|
| **detect** | Match if `package.json` ∧ (`svelte.config.js` ∨ vite config imports `@sveltejs/kit`). Vote for the `node-pnpm` backend. |
| **init** | `pnpm install`, optionally scaffold `vite.config.ts` if missing, contribute `.envrc` snippet (PATH munging for `node_modules/.bin`), add Node entries to the `.gitignore` template section, write a `sveltekit:` block to `.pyve/config` with the detected `pnpm` version. |
| **check** | `node` version drift vs. `.tool-versions`, `pnpm-lock.yaml` freshness vs. `package.json` mtime, `node_modules/` present, `svelte-check` clean (optional, severity=info), vitest config sanity (the [vite.config.ts:22](../../src/learningfoundry/sveltekit_template/vite.config.ts#L22) `process.env.VITEST` browser-conditions gate is the kind of invariant a plugin check could enforce). |
| **status** | `pnpm-lock.yaml` freshness, package count, Node version, last `pnpm install` timestamp. |
| **test** | Per-env: `vitest` (jsdom), `playwright` (browser), `svelte-check` (typechecker). Composes with the named-testenvs primitive — each is a named env declaring its run command. |
| **run** | `pyve run pnpm <args>` and `pyve run vite <args>` work, scoped to the plugin's activated PATH. |
| **purge** | Delete `node_modules/`. Preserve `package.json`, `pnpm-lock.yaml`, `svelte.config.js`, all user source — same discipline as the non-empty-`.env` rule. |

End user experience: in learningfoundry's repo, `pyve init` would do *both* the Python venv setup *and* the pnpm install, write *one* combined `.envrc`, manage *one* `.gitignore` template that knows about both ecosystems, and `pyve check` would report on the whole project's health in one pass.

## What pyve's charter has to change

- **[concept.md](pyve/concept.md) `solution_statement`** — generalize from "Python virtual environments" to "project environments, Python first-class plus opt-in plugins."
- **`scope` in-scope list** — add "plugin contract for non-Python ecosystems; ship at least one reference plugin in-tree."
- **`scope` out-of-scope list** — keep "Docker / cloud / Windows / GUI." Add "pyve does not replace ecosystem package managers (pnpm, cargo, go mod, …); plugins orchestrate them, mirroring how core orchestrates pip/conda."
- **`constraints`** — the "pure Bash, no runtime dependencies" constraint becomes load-bearing in a new way: **plugins must also be Bash** (or any executable matching a CLI contract that does not introduce a Python/Node interpreter requirement for *running pyve*). Otherwise pyve itself becomes ecosystem-dependent. Worth being deliberate.
- **`target_users`** — extend from "Python developers" to "Python developers (primary, home audience and carrier vector) + polyglot project owners whose Python tooling is the discipline anchor." The framing matters: Python devs reaching into other ecosystems remain the primary user, even when they're working in a Rust or SvelteKit subdirectory.

What does **not** change:
- macOS + Linux only.
- Pure Bash core, no runtime deps, no daemons.
- Orchestrate, don't replace.
- Idempotent.
- Never destroy user data.
- Secure defaults (`.env` `chmod 600`, self-healing `.gitignore`).
- Cloud-sync refusal.
- Apache 2.0.

## Requirements distilled

Charter-level (decide first):

A. **Plugin contract is a first-class part of pyve's identity, not a side-door extension mechanism.** If pyve adopts this, the contract is documented alongside the core CLI, not in a "for advanced users" appendix.
B. **Python is implemented as the first reference plugin (dog-food invariant).** The Python ecosystem support is built on the same plugin contract that third parties would use — not as a special-case core with an "extensions API" bolted on. This is the architectural truth behind the user-facing "Python first-class" framing: in user-facing language, Python is the default citizen; in implementation, Python *is just the first plugin*. Three benefits compound: (a) the contract is exercised from day one and stays honest; (b) the contract cannot regress without breaking the Python plugin first — so regressions are loud, not subtle; (c) future maintainers cannot grow a "Python is privileged" backdoor by accident. Tight coupling for performance/simplicity is fine; the contract boundary stays respected.
C. **SvelteKit is the second reference plugin.** It validates that the contract actually generalizes beyond the home ecosystem. If the contract supports Python and SvelteKit cleanly, it has earned its claim to be ecosystem-neutral in capability. Recommended choice because the use case is documented (this brief), the maintainer audience is already adjacent via learningfoundry, and "Python tests orchestrating a Node toolchain to validate a bundled SvelteKit template" exercises most of the contract surface in one repo.
D. **Backwards compatibility — a pure-Python project sees no change.** The Python plugin is the default; users do not learn a new concept; the plugin model is invisible to them unless they reach for it. Concretely: an existing `pyve init` on a `pyproject.toml`-only project does today exactly what it does after this lands.

Capability-level (only if charter accepted):

E. **Plugin discovery.** In-tree only for v1? Out-of-tree plugins via a published contract later? Recommend in-tree only for v1 — keeps the surface honest and the contract revisable while it's young.
F. **Multiple active plugins.** A monorepo with Python backend + SvelteKit frontend should run both plugins. Recommend: ordered list in `.pyve/config`, no "primary" designation — each plugin owns its config namespace, lifecycle hooks compose in declared order. Python's "first" status comes from being the default-included plugin, not from a privileged slot.
G. **`.pyve/config` schema versioning.** A plugin extending the schema needs a version field per plugin block. The core's `pyve_version` drift check ([features.md FR-5](pyve/features.md)) generalizes to per-plugin drift.
H. **Combined `.envrc`.** One file, contributed sections from core + each active plugin, marked with sentinel comments so `pyve update` can refresh plugin sections without touching user-authored content below.
I. **Combined `pyve check`.** One pass, per-plugin sections, exit-code roll-up (worst severity wins, matching the existing ladder).
J. **Combined smart purge.** Each plugin declares its "created vs. user-authored" inventory; `pyve purge` composes them.

## Position on whether to adopt this

This brief is written to *prompt* the decision, not to make it. The author of this revision believes the reframing is defensible *if* pyve is willing to absorb a charter expansion and *if* the SvelteKit reference plugin proves the contract is light enough to keep the pure-Bash, no-runtime-deps property. If either is doubtful, the right answer is "no" — and the named-testenvs work proceeds under the existing Python-only charter, leaving polyglot pain to be solved elsewhere.

## Open questions

1. **Is this actually pyve's job?** Or is a separate tool (`mypve`?, a project-environment-orchestrator that wraps pyve as the Python plugin from day one) cleaner, leaving pyve as-is? — **Recommended position: yes, this is pyve's job.** The carrier-audience argument is the deciding factor: pyve's home community (Python developers) is also the natural distribution vector for a polyglot orchestrator. Python devs bring pyve into the Rust/Node/Svelte/Docker projects they touch; the reverse path (a Rust dev discovering pyve cold) is much weaker. A separate tool would forfeit that distribution channel and start with no audience. The cost is a charter expansion; the benefit is a real audience already exists for the expanded charter.
2. **Plugin distribution model** — in-tree only for v1 (recommended), or contract-published-from-day-one?
3. **Plugin language constraint** — Bash only (preserves no-runtime-deps), or any executable satisfying a CLI contract? Recommendation leans Bash for v1: the Python reference plugin is already exercising it (dog-food), and a Bash-only floor preserves the "no runtime deps" property that pyve users rely on.
4. **Multiple-plugin composition order** — declared in config? Detection-order? Alphabetical? Matters for `.envrc` PATH precedence and for which plugin's `.gitignore` template section appears first.
5. **Relationship to the named-testenvs primitive** — do plugin-contributed envs sit *in* the named-testenvs namespace? **Recommended: yes — `pyve test --env vitest` works because the SvelteKit plugin declared a `vitest` env. One namespace, plugin-contributed.** This is also where Open Q 5 of the named-testenvs brief (the "what runs the tests" hook) lands: plugins declare the run command per env.
6. **Pyve in a no-Python project** — what happens to a project that is *only* SvelteKit (or only Rust)? The "Python plugin is the default" framing answers cleanly: the Python plugin is included but unused; only the active (detected or declared) plugins do work. Carrier-audience reasoning predicts this case is real but rare — a Python dev maintaining a Node-only side project. Worth confirming the UX is friendly (no spurious "Python not found" warnings) even though it's not the optimization target.

## Related

- [pyve-named-testenvs.md](pyve-named-testenvs.md) — the tactical sibling brief; UC5 punts polyglot to this doc.
- [pyve/concept.md](pyve/concept.md) — the charter this doc proposes evolving.
- [pyve/features.md](pyve/features.md) — the current capability surface that plugins would extend.
- [pyve/tech-spec.md](pyve/tech-spec.md) — the current implementation discipline (pure Bash, lib/ modular pattern, severity ladder) that plugins must respect.
- learningfoundry's [SvelteKit template](../../src/learningfoundry/sveltekit_template/) — the worked-example codebase for the reference plugin.
