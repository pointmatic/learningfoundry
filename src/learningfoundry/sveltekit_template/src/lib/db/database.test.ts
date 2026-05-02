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

describe('Database — concurrent getDb() on one instance', () => {
	beforeEach(() => {
		vi.resetModules();
		// Wipe fake-indexeddb wholesale — earlier tests leak open
		// sql.js Database instances which would block deleteDatabase.
		(globalThis as { indexedDB: IDBFactory }).indexedDB = new FDBFactory();
	});

	it('returns the same sql.js Database for N concurrent callers (Story I.v invariant, scoped to one instance)', async () => {
		const { Database } = await import('./database.js');
		const database = new Database();
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
		const database = new Database();
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
		(globalThis as { indexedDB: IDBFactory }).indexedDB = new FDBFactory();
	});

	it('two new Database() instances hold distinct internal sql.js Database refs (the testability win this refactor unlocks)', async () => {
		const { Database } = await import('./database.js');
		const a = new Database();
		const b = new Database();
		expect(a).not.toBe(b);
		const dbA = await a.getDb();
		const dbB = await b.getDb();
		expect(dbA).not.toBe(dbB);
	});
});
