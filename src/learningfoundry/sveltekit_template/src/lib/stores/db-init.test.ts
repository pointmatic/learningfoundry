// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { WasmAssetMissingError } from '$lib/db/database.js';

const mockGetDb = vi.fn();
vi.mock('$lib/db/index.js', () => ({
	database: {
		getDb: () => mockGetDb()
	}
}));

const { dbInit, initializeDatabase, resetDbInitForTests } = await import('./db-init.js');

beforeEach(() => {
	mockGetDb.mockReset();
	resetDbInitForTests();
});

describe('dbInit store (Story I.bb — layout-level wasm-missing surfacing)', () => {
	it('starts in pending state', () => {
		expect(get(dbInit)).toBe('pending');
	});

	it('transitions to ready when getDb() resolves', async () => {
		mockGetDb.mockResolvedValueOnce({});
		await initializeDatabase();
		expect(get(dbInit)).toBe('ready');
	});

	it('transitions to wasm-missing when getDb() rejects with WasmAssetMissingError', async () => {
		mockGetDb.mockRejectedValueOnce(new WasmAssetMissingError('/sql-wasm.wasm'));
		await initializeDatabase();
		expect(get(dbInit)).toBe('wasm-missing');
	});

	it('does not throw when getDb() rejects with WasmAssetMissingError', async () => {
		mockGetDb.mockRejectedValueOnce(new WasmAssetMissingError('/sql-wasm.wasm'));
		await expect(initializeDatabase()).resolves.toBeUndefined();
	});

	it('transitions to failed for non-WASM errors and does not re-throw', async () => {
		const errSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
		mockGetDb.mockRejectedValueOnce(new Error('idb is broken'));
		await initializeDatabase();
		expect(get(dbInit)).toBe('failed');
		errSpy.mockRestore();
	});

	it('is idempotent — second call does not re-invoke getDb()', async () => {
		mockGetDb.mockResolvedValue({});
		await initializeDatabase();
		await initializeDatabase();
		expect(mockGetDb).toHaveBeenCalledTimes(1);
	});
});
