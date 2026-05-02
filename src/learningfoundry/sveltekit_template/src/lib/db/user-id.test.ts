// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

const STORAGE_KEY = 'learningfoundry-user-id';
const UUID_V4_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

// vitest's jsdom env exposes `globalThis.localStorage` as a Proxy that
// only accepts string-string property writes (no method assignment).
// Replace the whole global with a Map-backed Storage stub so the real
// `user-id.ts` can call `getItem` / `setItem` / `removeItem`.
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

describe('getUserId', () => {
	beforeEach(() => {
		vi.resetModules();
		localStorage.removeItem(STORAGE_KEY);
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('returns a UUID v4 and persists it on a fresh localStorage', async () => {
		const { getUserId } = await import('./user-id.js');
		const id = await getUserId();
		expect(id).toMatch(UUID_V4_REGEX);
		expect(localStorage.getItem(STORAGE_KEY)).toBe(id);
	});

	it('returns the existing value on subsequent calls (no rotation)', async () => {
		const { getUserId } = await import('./user-id.js');
		const first = await getUserId();
		const second = await getUserId();
		expect(second).toBe(first);
	});

	it('two parallel callers on a fresh localStorage converge on the same UUID via the Web Lock', async () => {
		// Simulate `navigator.locks.request` as a real serialiser: queue
		// callbacks per lock name and run them strictly one at a time.
		const queue: Array<() => Promise<void>> = [];
		let busy = false;
		async function drain() {
			if (busy) return;
			busy = true;
			while (queue.length) {
				const next = queue.shift()!;
				await next();
			}
			busy = false;
		}
		const fakeLocks = {
			request: <T>(
				_name: string,
				_opts: LockOptions | ((lock: Lock | null) => Promise<T>),
				maybeCb?: (lock: Lock | null) => Promise<T>
			): Promise<T> => {
				const cb = (typeof _opts === 'function' ? _opts : maybeCb) as (
					lock: Lock | null
				) => Promise<T>;
				return new Promise((resolve, reject) => {
					queue.push(async () => {
						try {
							resolve(await cb({} as Lock));
						} catch (err) {
							reject(err);
						}
					});
					void drain();
				});
			}
		};
		vi.stubGlobal('navigator', { ...navigator, locks: fakeLocks });

		const { getUserId } = await import('./user-id.js');
		const [a, b, c] = await Promise.all([getUserId(), getUserId(), getUserId()]);
		expect(a).toBe(b);
		expect(a).toBe(c);
		expect(a).toMatch(UUID_V4_REGEX);
	});
});
