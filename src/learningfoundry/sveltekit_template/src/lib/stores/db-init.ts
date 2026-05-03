// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
/**
 * Layout-level database initialisation signal.
 *
 * Story I.bb: when `Database.getDb()` rejects with `WasmAssetMissingError`,
 * the learner has no UI signal that progress recording is broken. The
 * `+layout.svelte` mount calls `initializeDatabase()` once; failures
 * propagate to this store so a single layout-level banner can surface
 * the recording-paused state. Per-write rejections are swallowed in
 * `progress.ts` (the banner is the user-facing surface; UI components
 * shouldn't have to handle the rejection on every call site).
 *
 * Status values:
 * - `pending`  — initial; init has not yet resolved.
 * - `ready`    — DB is initialised and healthy.
 * - `wasm-missing` — `WasmAssetMissingError` was thrown; banner shows.
 * - `failed`   — non-WASM init failure; reserved for future surfacing.
 */
import { writable } from 'svelte/store';
import { database } from '$lib/db/index.js';
import { WasmAssetMissingError } from '$lib/db/database.js';

export type DbInitStatus = 'pending' | 'ready' | 'wasm-missing' | 'failed';

export const dbInit = writable<DbInitStatus>('pending');

let started = false;

/**
 * Drive the dbInit store by attempting `database.getDb()` once. Idempotent
 * across the layout's lifetime — repeated calls after the first are no-ops.
 * `resetDbInitForTests()` clears the latch so tests can re-run init.
 */
export async function initializeDatabase(): Promise<void> {
	if (started) return;
	started = true;
	try {
		await database.getDb();
		dbInit.set('ready');
	} catch (err) {
		if (err instanceof WasmAssetMissingError) {
			dbInit.set('wasm-missing');
			return;
		}
		dbInit.set('failed');
		// Non-WASM failures are still unexpected; surface to the console so
		// developers see them in the preview log even though the layout
		// banner only handles the WASM case today.
		console.error('Database init failed', err);
	}
}

export function resetDbInitForTests(): void {
	started = false;
	dbInit.set('pending');
}
