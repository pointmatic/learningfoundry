// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import 'fake-indexeddb/auto';
import FDBFactory from 'fake-indexeddb/lib/FDBFactory';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

// jsdom has no working `fetch` for sql.js's wasm load. Serve the bytes
// straight from disk so the real sql.js can initialise during tests.
beforeAll(() => {
	const here = dirname(fileURLToPath(import.meta.url));
	const wasmPath = resolve(here, '../../../static/sql-wasm.wasm');
	const wasmBytes = readFileSync(wasmPath);
	const realFetch = globalThis.fetch;
	globalThis.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
		const url = typeof input === 'string' ? input : input.toString();
		if (url.endsWith('sql-wasm.wasm')) {
			return Promise.resolve(
				new Response(wasmBytes, { headers: { 'content-type': 'application/wasm' } })
			);
		}
		return realFetch ? realFetch(input, init) : Promise.reject(new Error(`unmocked fetch: ${url}`));
	}) as typeof fetch;
});

// vitest's jsdom env exposes `globalThis.localStorage` as a Proxy that
// only accepts string-string property writes (no method assignment).
// The `Database` class lazy-resolves userId via `getUserId()` which
// touches localStorage; replace the whole global with a Map-backed
// Storage stub so that path works in tests too.
beforeAll(() => {
	const data = new Map<string, string>();
	const fakeStorage = {
		getItem: (k: string) => data.get(k) ?? null,
		setItem: (k: string, v: string) => {
			data.set(k, String(v));
		},
		removeItem: (k: string) => {
			data.delete(k);
		},
		clear: () => {
			data.clear();
		},
		key: (i: number) => Array.from(data.keys())[i] ?? null,
		get length() {
			return data.size;
		}
	};
	Object.defineProperty(globalThis, 'localStorage', {
		value: fakeStorage,
		writable: true,
		configurable: true
	});
});

function freshIdb() {
	(globalThis as { indexedDB: IDBFactory }).indexedDB = new FDBFactory();
}

// Open the underlying IDB store directly to plant or read raw blobs in
// the migration tests below — bypasses the `Database` class.
function rawIdbPut(key: string, value: Uint8Array): Promise<void> {
	return new Promise((res, rej) => {
		const open = indexedDB.open('learningfoundry', 1);
		open.onupgradeneeded = () => open.result.createObjectStore('progress');
		open.onsuccess = () => {
			const idb = open.result;
			const tx = idb.transaction('progress', 'readwrite');
			tx.objectStore('progress').put(value, key);
			tx.oncomplete = () => res();
			tx.onerror = () => rej(tx.error);
		};
		open.onerror = () => rej(open.error);
	});
}

function rawIdbGet(key: string): Promise<Uint8Array | null> {
	return new Promise((res, rej) => {
		const open = indexedDB.open('learningfoundry', 1);
		open.onupgradeneeded = () => open.result.createObjectStore('progress');
		open.onsuccess = () => {
			const idb = open.result;
			const tx = idb.transaction('progress', 'readonly');
			const req = tx.objectStore('progress').get(key);
			req.onsuccess = () => res((req.result as Uint8Array) ?? null);
			req.onerror = () => rej(req.error);
		};
		open.onerror = () => rej(open.error);
	});
}

describe('Database — concurrent getDb() on one instance', () => {
	beforeEach(() => {
		vi.resetModules();
		localStorage.removeItem('learningfoundry-user-id');
		freshIdb();
	});

	it('returns the same sql.js Database for N concurrent callers (Story I.v invariant, scoped to one instance)', async () => {
		const { Database } = await import('./database.js');
		const database = new Database('user-a');
		const refs = await Promise.all([
			database.getDb(),
			database.getDb(),
			database.getDb(),
			database.getDb(),
			database.getDb()
		]);
		for (const ref of refs) {
			expect(ref).toBe(refs[0]);
		}
	});

	it('a write through one getDb() reference is visible through every getDb() reference', async () => {
		const { Database } = await import('./database.js');
		const database = new Database('user-a');
		const refs = await Promise.all([database.getDb(), database.getDb(), database.getDb()]);
		refs[0].run(
			"INSERT INTO lesson_progress (module_id, lesson_id, status) VALUES ('mod-01', 'lesson-01', 'opened');"
		);
		await database.persist();
		for (const ref of refs) {
			const result = ref.exec(
				"SELECT status FROM lesson_progress WHERE module_id='mod-01' AND lesson_id='lesson-01';"
			);
			expect(result[0]?.values?.[0]?.[0]).toBe('opened');
		}
	});
});

describe('Database — independent instances', () => {
	beforeEach(() => {
		vi.resetModules();
		localStorage.removeItem('learningfoundry-user-id');
		freshIdb();
	});

	it('two new Database() instances hold distinct internal sql.js Database refs (the testability win this refactor unlocks)', async () => {
		const { Database } = await import('./database.js');
		const a = new Database('user-a');
		const b = new Database('user-b');
		expect(a).not.toBe(b);
		const dbA = await a.getDb();
		const dbB = await b.getDb();
		expect(dbA).not.toBe(dbB);
	});
});

describe('Database — per-user IDB partition (Story I.x)', () => {
	beforeEach(() => {
		vi.resetModules();
		localStorage.removeItem('learningfoundry-user-id');
		freshIdb();
	});

	it('different userIds write under their own IDB key and do not see each other\'s rows', async () => {
		const { Database } = await import('./database.js');

		const a = new Database('user-a');
		const dbA = await a.getDb();
		dbA.run(
			"INSERT INTO lesson_progress (module_id, lesson_id, status) VALUES ('mod-01', 'lesson-A', 'opened');"
		);
		await a.persist();

		const b = new Database('user-b');
		const dbB = await b.getDb();
		dbB.run(
			"INSERT INTO lesson_progress (module_id, lesson_id, status) VALUES ('mod-01', 'lesson-B', 'opened');"
		);
		await b.persist();

		const aSeesB = dbA.exec(
			"SELECT lesson_id FROM lesson_progress WHERE lesson_id='lesson-B';"
		);
		expect(aSeesB.length).toBe(0);
		const bSeesA = dbB.exec(
			"SELECT lesson_id FROM lesson_progress WHERE lesson_id='lesson-A';"
		);
		expect(bSeesA.length).toBe(0);

		// Verify the two records actually live under distinct keys.
		expect(await rawIdbGet('db:user-a')).not.toBeNull();
		expect(await rawIdbGet('db:user-b')).not.toBeNull();
	});
});

describe('Database — legacy IDB key migration (Story I.x)', () => {
	beforeEach(() => {
		vi.resetModules();
		localStorage.removeItem('learningfoundry-user-id');
		freshIdb();
	});

	it('on first init for a userId, pre-existing legacy `db` bytes are adopted and the legacy key deleted', async () => {
		const { Database } = await import('./database.js');

		// Bootstrap a "pre-v0.58.0" DB by writing a real sql.js export
		// under the legacy `db` key.
		const seed = new Database('seed-user');
		const seedDb = await seed.getDb();
		seedDb.run(
			"INSERT INTO lesson_progress (module_id, lesson_id, status) VALUES ('mod-01', 'lesson-01', 'complete');"
		);
		const legacyBytes = seedDb.export();
		freshIdb();
		await rawIdbPut('db', legacyBytes);
		expect(await rawIdbGet('db')).not.toBeNull();

		// New post-upgrade Database for `user-x` should see the migrated row.
		const after = new Database('user-x');
		const afterDb = await after.getDb();
		const result = afterDb.exec(
			"SELECT status FROM lesson_progress WHERE lesson_id='lesson-01';"
		);
		expect(result[0]?.values?.[0]?.[0]).toBe('complete');

		// Legacy key cleaned up.
		expect(await rawIdbGet('db')).toBeNull();
		// Per-user key now holds the data.
		expect(await rawIdbGet('db:user-x')).not.toBeNull();
	});

	it('is a no-op on second init (idempotent)', async () => {
		const { Database } = await import('./database.js');
		// First init — no legacy bytes — nothing to migrate.
		const a = new Database('user-y');
		await a.getDb();
		expect(await rawIdbGet('db')).toBeNull();
		// Second init — same instance — should not re-migrate or fail.
		await a.getDb();
		expect(await rawIdbGet('db')).toBeNull();
	});
});
