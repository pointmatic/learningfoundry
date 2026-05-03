# sql.js + WASM + IndexedDB — Robustness Patterns

Scope-specific reference for any project that uses [sql.js](https://github.com/sql-js/sql.js) (SQLite compiled to WebAssembly, persisted to IndexedDB) in a browser app. Captures gotchas, fixes, and design decisions discovered while building learningfoundry's progress-recording layer (Stories I.v through I.bb, v0.55.0–v0.63.0).

**Read this before:** wiring sql.js into a new project, or reviewing a sql.js integration in a host SvelteKit app (`<QuizBlock>`-style embed) where you don't own the asset pipeline.

**Skip this if:** you're using a server-side SQLite (better-sqlite3, libsql, etc.) — none of the WASM-fetch / IndexedDB issues apply.

---

## The four gotchas

### 1. sql.js's module-level state caches successful loads

`initSqlJs(...)` succeeds → sql.js stashes the compiled wasm in module scope. The next call returns the cached value. So far, so normal.

The problem: **if a later wasm fetch 404s, sql.js's own rejection path is unreliable** — it can return a `Database` instance that "works" but is unbacked, or report success on stale cached state. The 404 shows up only as a CLI/network log; consumers see queries silently fail or, worse, succeed-then-vanish.

**This is the most expensive bug in the set.** It manifests as: every progress write rejects, the UI shows no checkmarks, no in-progress icons, no error — and the only signal is the dev tools network panel. Diagnosed wrong, you'll go hunting in the persistence layer for hours.

### 2. WASM asset provisioning is fragile when there are two sources of truth

Two-source supply chains rot. The learningfoundry pre-fix had:

- A template `static/` directory rebuilt on every iterate-on-content rebuild (didn't ship the wasm — gitignored)
- A `pnpm postinstall` hook that copied `node_modules/sql.js/dist/sql-wasm.wasm` into place — only ran when `pipeline.run_preview` chose to actually `pnpm install`, which it skipped on `DepState.UNCHANGED`

The two paths cancelled each other on every content rebuild. Static/ got wiped; postinstall didn't re-run. Result: silent recording failures from the second build onward.

**Generalizes to any setup where:** template/scaffold rebuilds touch the same directory as a package-manager hook, or a CDN deploy and a CI build both write the same path, or a host SvelteKit app's build pipeline expects a hand-copied file in `static/` that's easy to forget.

### 3. Per-write rejections cascade silently through every UI call site

Once `Database.getDb()` rejects, every read and write in the repo layer rejects. UI components that just `await progressRepo.markLessonComplete(...)` without a `.catch` get an unhandled promise rejection — fine for diagnostics, useless for the user.

**The wrong fix:** add `try/catch` at every UI call site. You'll miss some, the contract grows brittle, and the user still has no idea what's happening.

**The right fix:** surface the failure *once* at a layout-level boundary; suppress the rejection at the repo boundary so UI components don't have to defend on every call.

### 4. IndexedDB keying is hard to change later — pick a partitioning strategy day one

learningfoundry pre-v0.58.0 stored everything under an unkeyed `db` IDB record. v0.58.0 added per-user partitioning (`db:${userId}`) and shipped a one-shot legacy migration. The migration is ~30 lines but had to be exactly right or learner data would silently vanish.

Common partitioning axes:

- **Per-user** (learningfoundry): UUID v4 in `localStorage`, swap for auth ID later
- **Per-quiz** (quizazz): `quizazz-<quizName>` — multiple DBs in the same origin
- **Per-app/single** (smallest): one DB, no key

Pick the most permissive axis you can reasonably commit to. Going from "single DB" to "per-user" requires a migration; going the other way is rare and easy.

---

## The patterns (fixes)

### Pattern A: HEAD-fetch precheck + typed error class

Probe the wasm asset *before* delegating to `initSqlJs`, and throw a typed error if it's unavailable. See [database.ts:39-50, 154-167](../../src/learningfoundry/sveltekit_template/src/lib/db/database.ts).

```ts
export class WasmAssetMissingError extends Error {
    readonly assetUrl: string;
    constructor(assetUrl: string, cause?: unknown) {
        super(
            `sql.js wasm asset is unavailable at ${assetUrl}. ` +
                `Recording is disabled until the dev server can serve this file.`
        );
        this.name = 'WasmAssetMissingError';
        this.assetUrl = assetUrl;
        if (cause !== undefined) (this as { cause?: unknown }).cause = cause;
    }
}

async #assertWasmAssetAvailable(): Promise<void> {
    let response: Response;
    try {
        response = await fetch(WASM_ASSET_URL, {
            method: 'HEAD',
            cache: 'no-store'
        });
    } catch (err) {
        throw new WasmAssetMissingError(WASM_ASSET_URL, err);
    }
    if (!response.ok) {
        throw new WasmAssetMissingError(WASM_ASSET_URL);
    }
}
```

**Why HEAD + `cache: 'no-store'`:** the response body isn't needed (sql.js will fetch it anyway), and `no-store` defeats both the browser cache and any CDN edge that might be serving stale 200s for a removed asset. The precheck is what makes the failure deterministic and caller-visible regardless of sql.js's internal cache state.

### Pattern B: Init memoization (one in-flight init per Database instance)

Concurrent callers must share a single init promise — otherwise you get duplicate IndexedDB opens, duplicate legacy migrations, and a race where the second caller observes a half-initialised state. See [database.ts:96-113](../../src/learningfoundry/sveltekit_template/src/lib/db/database.ts#L96-L113).

```ts
async getDb(): Promise<SqlDatabase> {
    if (this.#db) return this.#db;
    if (!this.#dbInitPromise) {
        this.#dbInitPromise = (async () => {
            // ...userId resolution, sql.js init, legacy migration, IDB load...
            this.#db = db;
            return db;
        })();
    }
    return this.#dbInitPromise;
}
```

The same pattern wraps `#initSqlJs` — see [database.ts:134-152](../../src/learningfoundry/sveltekit_template/src/lib/db/database.ts#L134-L152). Two memoization layers because sql.js init and DB init are separable lifecycles.

### Pattern C: Single-source asset provisioning, build-time errors over runtime 404s

Pick *one* owner for the wasm asset and make every other path stop touching it. Convert "the file is missing" from a runtime 404 into a build-time error, so the failure surfaces during the developer's iteration loop rather than the learner's.

learningfoundry's [pipeline.py `_ensure_sql_wasm`](../../src/learningfoundry/pipeline.py) copies `output_dir/node_modules/sql.js/dist/sql-wasm.wasm` → `output_dir/static/sql-wasm.wasm` unconditionally, raising `GenerationError` if the source is absent. The template's `package.json` has no `postinstall` (removed in I.aa) and `static/sql-wasm.wasm` is in [generator.py `_PRESERVED_PATHS`](../../src/learningfoundry/generator.py) so atomic-copy doesn't wipe it. Belt-and-braces.

**For a host-integration scenario** (npm package consumed by third-party apps), the host owns `static/`, so build-time enforcement isn't possible from the package side. Two alternatives:

1. **Bundle the wasm via Vite asset imports** — `import wasmUrl from 'sql.js/dist/sql-wasm.wasm?url'; initSqlJs({ locateFile: () => wasmUrl });`. Vite emits the file into the host's build output and rewrites the URL. Eliminates the entire class of "host forgot to copy" failures, sidesteps pnpm's strict-layout caveat (transitive deps live under `.pnpm/<pkg>@<ver>/node_modules/<pkg>/` and aren't at the top-level path npm would use).
2. **At minimum, ship Pattern A** — even if hosts have to copy, the failure is loud and typed instead of silent and opaque.

### Pattern D: Repo-boundary swallow for typed errors that are surfaced elsewhere

Once a layout-level signal exists (Pattern E), per-call rejections become information duplicates. Swallow the *typed* error at the repo boundary; let untyped errors propagate. See [progress.ts](../../src/learningfoundry/sveltekit_template/src/lib/db/progress.ts):

```ts
async markLessonComplete(moduleId: string, lessonId: string): Promise<void> {
    try {
        const db = await this.#database.getDb();
        db.run(/* ... */);
        await this.#database.persist();
    } catch (err) {
        if (err instanceof WasmAssetMissingError) return;
        throw err;
    }
}
```

**Read methods return their "no progress yet" sentinel** (`null` for single-row getters, an empty `not_started` shape for `getModuleProgress`) so the dashboard renders the empty state rather than an error page. A failed read during initial render is a worse UX than a failed write.

**Document the swallow rule in the file's module comment** so a future maintainer doesn't refactor the catches away thinking they're dead code.

### Pattern E: Layout-level surface (single signal, single banner)

For app-shell projects: a `dbInit` writable store driven by a one-shot `initializeDatabase()` call from the root layout. Status enum: `pending` | `ready` | `wasm-missing` | `failed`. The banner reads the store. See [stores/db-init.ts](../../src/learningfoundry/sveltekit_template/src/lib/stores/db-init.ts) and [components/RecordingPausedBanner.svelte](../../src/learningfoundry/sveltekit_template/src/lib/components/RecordingPausedBanner.svelte).

For embedded-component projects (the host owns the layout): expose the typed error to the host via an `onerror` callback prop or a `CustomEvent` on the component root, optionally render an internal banner inside the component bounds as a fallback. **Do not** install a layout-level singleton store from inside an embed component — you don't own the host's reactive graph.

---

## Decisions left to the project

These are the axes where the right answer depends on app shape; don't pre-bake them into a shared library until you've seen at least three call sites.

| Axis | learningfoundry | quizazz | Notes |
|------|-----------------|---------|-------|
| Partitioning key | `db:${userId}` (UUID in `localStorage`) | `quizazz-<quizName>` | Auth-issued IDs swap in later for either |
| Migration strategy | One-shot legacy `db` → `db:${userId}` | None | Migration is ~30 lines and must be idempotent |
| Cross-tab anti-clobber | Web Locks (`navigator.locks.request`) on bootstrap; not solved for writes | Last-writer-wins | Defer until evidence of multi-tab workflows |
| WASM provisioning | Python pipeline copies into `static/` | Host-app copies into `static/` | Vite asset-import bundling avoids both |
| Failure surface | Layout-level banner | TBD (host-supplied via callback) | Embed components shouldn't own the layout |
| Repo-boundary policy | Swallow typed wasm errors; reads return empty | Same recommendation | Document the rule inline |

---

## What this doc doesn't cover

- **Cross-tab synchronization.** Web Locks bootstrap solves the *userId* race, not concurrent writes. Two tabs writing to the same DB still last-writer-wins on the IDB blob. Solve when there's evidence of multi-tab learner workflows.
- **Schema migrations.** sql.js's `db.run(DDL)` with `CREATE TABLE IF NOT EXISTS` covers additive changes. Column drops, type changes, and back-fills are not addressed here; they need explicit version-tracking rows and an in-app migration runner.
- **Multi-DB management.** quizazz opens a separate DB per quiz. Cross-DB queries, lifecycle (open/close), and quota management are out of scope.
- **Quota / `QuotaExceededError`.** Long-running learner sessions can hit IDB quota limits. Detect, surface, and offer purge — not implemented in either project today.
- **Service worker interactions.** A service worker that caches `/sql-wasm.wasm` with the wrong cache strategy can re-introduce the cache-poisoning failure even after the asset is fixed at origin. None of the current projects use service workers.
- **Server-side persistence sync.** Anything that mirrors the IDB state to a server (offline-first PWA pattern) is fundamentally out of scope.

---

## Cross-reference: where each pattern lives in learningfoundry

| Pattern | File | Story |
|---------|------|-------|
| `WasmAssetMissingError` class | [database.ts:39-50](../../src/learningfoundry/sveltekit_template/src/lib/db/database.ts#L39-L50) | I.aa (v0.61.0) |
| HEAD-fetch precheck | [database.ts:154-167](../../src/learningfoundry/sveltekit_template/src/lib/db/database.ts#L154-L167) | I.aa |
| Init memoization | [database.ts:96-113, 134-152](../../src/learningfoundry/sveltekit_template/src/lib/db/database.ts) | I.v (v0.55.0) |
| Per-user partitioning + legacy migration | [database.ts:206-236](../../src/learningfoundry/sveltekit_template/src/lib/db/database.ts#L206-L236), [user-id.ts](../../src/learningfoundry/sveltekit_template/src/lib/db/user-id.ts) | I.x (v0.58.0) |
| Build-time WASM provisioning | [pipeline.py `_ensure_sql_wasm`](../../src/learningfoundry/pipeline.py) | I.aa |
| Repo-boundary swallow | [progress.ts](../../src/learningfoundry/sveltekit_template/src/lib/db/progress.ts) | I.bb (v0.63.0) |
| Layout-level dbInit store | [stores/db-init.ts](../../src/learningfoundry/sveltekit_template/src/lib/stores/db-init.ts) | I.bb |
| Recovery banner | [components/RecordingPausedBanner.svelte](../../src/learningfoundry/sveltekit_template/src/lib/components/RecordingPausedBanner.svelte) | I.bb |
| FR-4 user-visible requirement | [features.md FR-4 "Recording-paused state"](features.md#fr-4-in-browser-progress-tracking) | I.bb |

---

## When to revisit

- A *third* sql.js consumer appears in the Pointmatic codebase. Two consumers don't justify a shared library; three usually do.
- learningfoundry and quizazz independently grow features that mirror each other (schema versioning, multi-DB, sync). That's the signal that the abstraction shape has firmed up enough to extract.
- A new sql.js release changes the failure semantics (e.g., the module-level cache behavior, the `locateFile` contract, the wasm filename). Review Pattern A and update the precheck.
- Browser quota / `QuotaExceededError` becomes a real user complaint. Add a "What this doesn't cover" → in-scope migration.
