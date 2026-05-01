# Future Testing Infrastructure Options

This document captures four testing-infrastructure options that were
considered and deferred during Story I.q (v0.52.0) and earlier. None is
needed for the current backlog. Each has a concrete trigger condition; if
that trigger fires, the relevant section here is the starting point for
the new story.

---

## Status today

The SvelteKit template runs a two-tier test stack:

1. **Vitest in jsdom** — unit-level coverage for pure logic (helpers,
   stores, db-mocked operations) and component-level coverage for
   rendering and event wiring (Svelte 5 mount via
   `@testing-library/svelte`, enabled by Story I.q's
   `resolve.conditions: ['browser']` config).
2. **Playwright e2e (`pnpm e2e`)** — full-stack coverage against the
   built static site for behaviours that require a real browser
   (navigation lifecycle, real `IntersectionObserver` geometry, real
   scroll containers). Skipped when Chromium binaries aren't installed.

This stack covers every test that has been needed through v0.52.0.
The four options below are real upgrades that would buy specific
capabilities, but each has a cost that is not worth paying speculatively.

---

## 1. `@vitest/browser` + Playwright

**What it is.** Replace vitest's jsdom environment with a real browser
process. Each test boots Chromium (or Firefox/WebKit), runs the test
inside a real DOM, and reports back. Activated via `test.browser` config:

```ts
test: {
  browser: { enabled: true, provider: 'playwright', name: 'chromium' }
}
```

**What jsdom gets wrong that this fixes.**

- **Layout.** jsdom never lays out the DOM. `getBoundingClientRect()`
  returns zeros, `IntersectionObserver` doesn't actually fire on scroll,
  scroll containers don't scroll. That's why Story I.q's
  `TextBlock.observer.test.ts` had to assert `style.height === '1px'`
  rather than `getBoundingClientRect().height > 0` — jsdom would always
  fail the latter.
- **Rendering APIs.** `Canvas`, `WebGL`, `requestAnimationFrame` timing,
  `IntersectionObserver` with real geometry, `ResizeObserver`, native
  focus management. jsdom stubs most of these or omits them.
- **CSS-driven behaviour.** Anything that depends on actual computed
  styles (e.g. testing that a Tailwind class produced the expected
  `display: none`) silently passes in jsdom.

**Cost.**

- Browser binaries: ~150 MB Chromium. Already a friction point — the
  Playwright e2e leg currently skips in our smoke for exactly this reason.
- Per-test overhead: ~50–200 ms per test for browser-side spin-up. The
  current ~134-test vitest suite finishes in ~1.5 s in jsdom; in
  browser mode it would be 30–60 s.
- CI complexity: needs `playwright install` step.
- Library APIs subtly differ between vitest jsdom and vitest browser
  modes; `@testing-library/svelte` quirks especially.

**Trigger.** A unit test that needs real layout / scroll / observer
geometry, where dropping to e2e is too slow. Example: testing that
`<main>` actually scrolls and the end-of-block sentinel actually
intersects, in a tighter loop than `pnpm preview`-driven Playwright.

**Recommendation when triggered.** Write the test in e2e first; only
escalate to `@vitest/browser` if the e2e variant is too slow or too
brittle for the iteration cadence the work needs. Don't enable it
template-wide — gate it to a single `*.browser.test.ts` glob so the
fast jsdom suite remains the default.

---

## 2. Visual regression / screenshot testing

**What it is.** Render a component (or a full page), screenshot it, diff
against a checked-in baseline image. Fail the test if the diff exceeds a
pixel-similarity threshold. Tools: Playwright's built-in
`toHaveScreenshot()`, Percy, Chromatic, Loki.

**What it catches that text-based tests miss.**

- CSS regressions (a Tailwind class change that subtly shifts a button's
  padding).
- Specificity / cascade bugs (a global style override breaking one
  component).
- Theming bugs (dark-mode CSS variable not threading through).
- Layout regressions (something pushing into the next column).

**Cost.**

- **Baseline maintenance.** Every legitimate UI change requires
  re-approving the baseline. This is the single biggest cost — teams
  either get strict (slow review velocity) or lax (regressions slip
  through).
- **Flakiness.** Anti-aliasing, font rendering, OS-level differences.
  Locally vs. CI vs. macOS vs. Linux all produce slightly different
  pixels. Threshold tuning becomes its own ongoing project.
- **Per-platform baselines.** If devs run on Mac and CI runs on Linux,
  you need baselines per platform or the test only runs in CI.
- **Storage.** Baseline images live in git or a CDN. Adds repo size or
  external infrastructure.

**Trigger.** A CSS-shaped feature where pixel correctness is the value
proposition (a richer dashboard, a learner-facing theming option, a
print stylesheet, a public design system).

**Recommendation when triggered.** Adopt cautiously and budget for
baseline maintenance from day one. Start with Playwright's built-in
`toHaveScreenshot()` — no extra service required, baselines live in git.
Move to a managed service (Chromatic/Percy) only if review workflow
demands it.

**Important caveat.** None of the v0.37–v0.52 regressions were
CSS-shaped (sentinel zero-height, stale video iframe, navigation
routing — all logic bugs). Visual regression would not have caught any
of them. For an e-learning curriculum tool where the visual chrome is
sparse, the ROI is low; stay alert for the trigger but don't reach for
this speculatively.

---

## 3. Vitest projects (server suite vs. client suite)

**What it is.** Vitest's "projects" feature splits one config into
multiple independent test runs with different settings. Common pattern
in SvelteKit:

```ts
test: {
  projects: [
    {
      name: 'client',
      test: {
        environment: 'jsdom',
        resolve: { conditions: ['browser'] },
        include: ['src/**/*.client.test.ts']
      }
    },
    {
      name: 'server',
      test: {
        environment: 'node',
        include: ['src/**/*.server.test.ts']
      }
    }
  ]
}
```

**What it solves.** SvelteKit code can run in two contexts:

- **Client.** What `+page.svelte` does in a browser.
- **Server.** What `+page.server.ts`, `hooks.server.ts`,
  `+layout.server.ts` do during SSR or as API endpoints.

These contexts have different globals, different module resolution,
different APIs. A `+page.server.ts` test that imports node's `fs` should
not be loaded with `resolve.conditions: ['browser']`. A `+page.svelte`
mount test that calls `document.querySelector` should not run in
node-only mode.

**Why our template skipped it.** The SvelteKit template is
**client-only** — there is no `+page.server.ts`, no SSR. We use
`adapter-static` and the layout exports `ssr = false; prerender =
false`. Every test in the codebase exercises client code. One project
covers everything; splitting into two would mean naming half the files
`*.client.test.ts` for no benefit.

**Trigger.** A Svelte 5 component test that calls the `svelte/server`
`render` API (e.g. testing how a component's static HTML output handles
a particular prop). This is a legitimate pattern but we haven't needed
it; the Story I.o attempt to use `svelte/server` failed precisely
because our config doesn't have the server-side compilation wired, and
projects mode is the canonical fix.

**Recommendation when triggered.** Adopt — it's a 30-minute config
change once a `svelte/server` test actually arrives. Adopting
pre-emptively means maintaining two suites for one set of tests, which
is the wrong direction.

---

## 4. Storybook (or other component harnesses)

**What it is.** Standalone component playground. Each component gets a
`Component.stories.ts` declaring "stories" (pre-configured prop sets);
Storybook renders them in an interactive browser UI. Adjacent: Histoire
(Vue/Svelte-focused), Ladle (lightweight Vite-native).

**What it actually offers (sorting hype from value).**

- **Manual exploration.** Designers / PMs can browse component variants
  without booting the app. Real value if non-engineers review components.
- **Documentation.** Stories double as visual docs. Real value if the
  component library is reused across multiple apps.
- **A11y / interaction add-ons.** Storybook has plugins for axe-core,
  focus state, keyboard nav. Useful but available standalone.
- **Visual regression.** Often paired with Chromatic for option 2 above.
  (Same caveats apply.)
- **"Component testing"** — Storybook has its own play-functions test
  runner. Almost always weaker than vitest + testing-library and adds
  another runtime.

**Cost.**

- ~50 MB of devDependencies, its own build pipeline, its own config
  files.
- Stories drift from the components they document — constant
  maintenance overhead unless someone owns it.
- Adds a third render context (jsdom unit + Playwright e2e + Storybook).
  Each context has slightly different module resolution behaviour; bugs
  appear in one and not the others.

**Why our template skipped it.**

- Our app is single-deployment (one curriculum, one frontend). No
  component library reuse.
- No designers in the loop on component variants.
- Documentation lives in `docs/specs/tech-spec.md` as prose; the
  components themselves are small (~50–150 lines each); a separate
  browsable catalog adds little.
- Visual regression already declined in option 2.

**Trigger.** Any of: (a) the component library getting reused outside
this app, (b) a non-engineer review workflow that needs interactive
component browsing, (c) shipping a public design system / theme.

**Recommendation when triggered.** Skip indefinitely. If the trigger
fires, evaluate **Histoire** over Storybook — significantly lighter for
Svelte specifically and avoids most of the maintenance overhead.

---

## Decision matrix

| Option | Trigger | Recommendation if triggered |
|---|---|---|
| `@vitest/browser` | A unit test needs real layout / scroll / observer geometry | Adopt — but write the test in e2e first; only escalate if e2e is too slow |
| Visual regression | A CSS-shaped feature where pixel correctness is the value | Adopt cautiously; budget for baseline maintenance from day one |
| Vitest projects | A `svelte/server` rendering test | Adopt — 30-minute config change |
| Storybook / Histoire | Component reuse outside this app, or non-engineer review workflow | Prefer Histoire; budget for story drift |

None of these is needed for the current backlog (Stories I.s and I.t
fit cleanly inside the Story I.q infrastructure). All are easy to add
when the triggering need surfaces. The cost of adopting them
pre-emptively — extra build complexity, extra dependencies, extra
maintenance — outweighs the option value of having them ready.

---

## Adjacent practices we already do (for context)

- **Layered coverage.** Pure-logic helpers (`createViewportTracker`,
  `createBlockTracker`, `computeAutoExpand`, `resolveGoNext`) are tested
  in isolation; component-level mount tests assert markup and event
  wiring; e2e tests cover real-browser behaviour. Each layer remains
  the fastest debugging surface for the bugs that occur at its layer.
- **Fixture-decoupled e2e.** `e2e/fixtures/curriculum.json` plus
  `page.route('**/curriculum.json', …)` interception keeps the e2e
  harness stable against unrelated curriculum drift in the smoke build.
- **Anti-regression source assertions.** Where mount tests are
  infeasible (Story I.o pre-Story-I.q), source-text assertions on
  `.svelte` files lock in specific markup invariants. Brittle to
  formatting but cheap and reliable; useful as a stopgap until proper
  mount coverage exists.
