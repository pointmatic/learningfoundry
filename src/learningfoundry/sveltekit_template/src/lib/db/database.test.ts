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

describe('getDb — concurrent init', () => {
	beforeEach(() => {
		vi.resetModules();
		// Wipe fake-indexeddb wholesale — earlier tests leak open
		// Database instances from the race, which would block a
		// `deleteDatabase` call indefinitely.
		(globalThis as { indexedDB: IDBFactory }).indexedDB = new FDBFactory();
	});

	it('returns the same Database instance for N concurrent callers', async () => {
		const { getDb } = await import('./database.js');
		const refs = await Promise.all([getDb(), getDb(), getDb(), getDb(), getDb()]);
		for (const ref of refs) {
			expect(ref).toBe(refs[0]);
		}
	});

	it('a write through one reference is visible through every reference', async () => {
		const { getDb, persistDb } = await import('./database.js');
		const refs = await Promise.all([getDb(), getDb(), getDb()]);
		refs[0].run(
			"INSERT INTO lesson_progress (module_id, lesson_id, status) VALUES ('mod-01', 'lesson-01', 'opened');"
		);
		await persistDb();
		// With the race, refs[1]/refs[2] are different Database instances
		// and won't see the row written through refs[0].
		for (const ref of refs) {
			const result = ref.exec(
				"SELECT status FROM lesson_progress WHERE module_id='mod-01' AND lesson_id='lesson-01';"
			);
			expect(result[0]?.values?.[0]?.[0]).toBe('opened');
		}
	});
});
