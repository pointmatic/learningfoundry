<!-- Copyright (c) 2026 Michael Smith -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

**Superseded by `docs/specs/sql-js-wasm-robustness.md` Pattern F**

# LearningFoundry spec: `sql.js` browser ESM import breakage in preview

Status: **fixed in v0.79.2** (Story J.y) — via Option E + Option C, not Option A or B. The Option A "pin to `>=1.12.0 <1.13.0`" recommendation in this spec is *unreachable* (the only sub-1.13 version on npm is `1.12.0`, and its emscripten runtime breaks the vitest+jsdom test infra). Option B's subpath import has the same Node-vs-browser bundle-flavor problem. The landed fix scopes [vite.config.ts](../../src/learningfoundry/sveltekit_template/vite.config.ts)'s `optimizeDeps.exclude: ['sql.js']` to `process.env.VITEST` only, restoring Vite's CJS→ESM dep pre-bundling in dev/prod while preserving the vitest 4.x WASM-magic-header workaround; combined with an Option C `CjsEsmInteropError` backstop in [database.ts](../../src/learningfoundry/sveltekit_template/src/lib/db/database.ts) for future-drift visibility. See Story J.y for details.
Target package: `learningfoundry` SvelteKit template (`sveltekit_template/`)
Discovered against: learningfoundry v0.79.1, sql.js@1.14.1 (resolved from `^1.12.0`), Vite v8.0.14
Discovery context: a project preview server, clicking "Start module →" on Module 1

## Problem

In the generated SvelteKit app, the home page renders fine but any module/lesson route (`/{moduleId}/{lessonId}`) renders a "500 Internal Error" inside the page body. The dev server reports:

```
SyntaxError: The requested module '/node_modules/.../sql.js/dist/sql-wasm-browser.js?v=...'
  does not provide an export named 'default'
Database init failed TypeError: initSqlJsFn is not a function
> src/lib/db/database.ts:171:22
    const SQL = await initSqlJsFn({ locateFile: () => WASM_ASSET_URL });
```

The home page renders because it does not call `progressRepo` paths that depend on the DB; lesson and assessment routes do, so the unhandled rejection propagates to SvelteKit's error boundary.

## Root cause

Three things compose into the failure:

1. `sveltekit_template/package.json` pins `"sql.js": "^1.12.0"`. pnpm currently resolves this to **1.14.1**.
2. `sql.js@1.14.1`'s `dist/sql-wasm-browser.js` is a UMD-style script with the export wired only through CommonJS:

   ```js
   if (typeof exports === 'object' && typeof module === 'object'){
       module.exports = initSqlJs;
       module.exports.default = initSqlJs;
   }
   ```

   The package has no `"type": "module"` and no ESM `export default` statement. In a pure browser-ESM context none of the export branches runs, so the file exposes nothing.
3. `sveltekit_template/vite.config.ts` declares `optimizeDeps: { exclude: ['sql.js'] }` (added per upstream Story J.w to keep vitest 4.x's dep-optimizer from parsing the `sql-wasm.wasm` binary). This is the right call for tests but it also disables Vite's CJS→ESM pre-bundling for `sql.js` at dev-server time, so the browser receives the un-converted UMD file directly — and `(await import('sql.js')).default` is `undefined`.

So the dev-server preview path lost its CJS-interop layer once the optimizer-exclude was added, and the bug only surfaced when `sql.js@1.13+` stopped happening to "work by accident" through whatever fallback browsers were tolerating.

## Affected files in `sveltekit_template/`

- `package.json` (line 21) — dependency range
- `src/lib/db/database.ts` (line 170) — `(await import('sql.js')).default`
- `vite.config.ts` (line 14) — `optimizeDeps: { exclude: ['sql.js'] }`

## Proposed fix (upstream)

Pick one of the following; option A is the smallest behavioral change.

### Option A — narrow the dep-range to pre-1.13

In `sveltekit_template/package.json`:

```json
"sql.js": ">=1.12.0 <1.13.0"
```

Verify that 1.12.x still ships the browser bundle in a shape Vite can interop. This is a one-line change and preserves the existing import in `database.ts`.

Cost: floats `sql.js` indefinitely on a 1.12 line. Acceptable if 1.12.x is still maintained or if upstream sql.js republishes 1.13+ with ESM exports.

### Option B — switch to the explicit-subpath import

Replace the bare `import('sql.js')` in `database.ts` with the subpath that ships ESM-compatible defaults:

```ts
const initSqlJsFn = (await import('sql.js/dist/sql-wasm.js')).default;
```

`sql-wasm.js` (the non-browser entry that `package.json#exports.default` points at) sets `module.exports = initSqlJs` *and* still works in browser context because the WASM is fetched via `locateFile`. Combined with keeping `optimizeDeps.exclude` in place, this avoids the vitest-4.x WASM-parse issue *and* gives the browser something Vite's interop can resolve.

Cost: the `browser` condition in sql.js's `exports` is bypassed; verify that the non-browser bundle doesn't pull in Node built-ins (`fs`, `path`) at runtime in the dev server.

### Option C — defensive import with explicit interop guard

```ts
const mod = await import('sql.js');
const initSqlJsFn: typeof initSqlJs =
  (mod as unknown as { default?: typeof initSqlJs }).default ?? (mod as unknown as typeof initSqlJs);
if (typeof initSqlJsFn !== 'function') {
  throw new Error('sql.js did not expose an initializer — likely a CJS/ESM interop mismatch (see upstream issue).');
}
```

Cost: papers over the dep-version drift rather than fixing it; will silently fall back if a future sql.js drops the CJS branch too. Recommend pairing with option A.

### Recommendation

**Option A** as the immediate fix (smallest blast radius, preserves the test-side `optimizeDeps.exclude`), with **Option C**'s typed error layered in defensively so the *next* time this drifts the preview surfaces a typed error instead of a 500.

## Test coverage gap

No upstream test currently exercises `Database.getDb()` end-to-end in a real browser context — the existing test suite mocks `sql.js` via `vi.mock` (per the `vite.config.ts` comment), which is exactly what prevented the CJS/ESM mismatch from surfacing in CI. A playwright-style smoke test that loads `/{moduleId}/{lessonId}` in a real browser against a generated `dist/` would catch this class of bug.

## Consumer-side workaround (temporary, applied in `dist/`)

Until upstream lands a fix, the consumer can pin a working sql.js in the generated tree (preserved across `learningfoundry preview` runs because the pipeline preserves `node_modules/` and `pnpm-lock.yaml` and skips `pnpm install` when deps are "up to date"):

```bash
cd dist && pnpm add sql.js@1.12.2
```

This pins the resolution in `dist/pnpm-lock.yaml`. The next `learningfoundry build` will overwrite `dist/package.json` (reverting to the `^1.12.0` range) but the lock file's pin survives until something triggers a fresh `pnpm install` — at which point repeat the workaround. The workaround is documented in consumer's `stories.md` D.a.21 fix story and is **not** wired into the project Makefile (kept manual on purpose so the upstream fix doesn't get masked).
