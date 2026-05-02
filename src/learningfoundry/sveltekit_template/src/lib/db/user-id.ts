// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
/**
 * Pre-auth `userId` partition key.
 *
 * A UUID v4 stored in `localStorage`. `localStorage` is origin-scoped, so
 * two tabs of the same browser converge on the same value once written.
 * The very-first-visit two-tab race — where neither tab has written the
 * UUID yet — is resolved by wrapping the read-or-create in a Web Lock so
 * concurrent bootstraps converge on a single UUID.
 *
 * When auth lands, the swap is a key-rename rather than a schema
 * migration: replace this localStorage value with the auth-issued user ID
 * and rename the IDB key in `Database` once.
 */

const STORAGE_KEY = 'learningfoundry-user-id';
const LOCK_NAME = 'lf-user-id-bootstrap';

/**
 * Return the UUID v4 for this browser, generating and persisting one on
 * first call. Concurrent first-call invocations across tabs converge on
 * a single value via `navigator.locks`; on browsers without Web Locks
 * (Safari < 15.4) the bootstrap is racy but the window is small.
 */
export async function getUserId(): Promise<string> {
	const existing = localStorage.getItem(STORAGE_KEY);
	if (existing) return existing;

	const locks = (navigator as Navigator & { locks?: LockManager }).locks;
	if (!locks) {
		// Fallback: no Web Locks. Two simultaneous first-visit tabs may
		// each generate a UUID, with the loser orphaning a few writes
		// to a UUID that gets overwritten. Acceptable for the rare
		// (Safari < 15.4) browser × (two-tab cold start) intersection.
		return generateAndStore();
	}

	return locks.request(LOCK_NAME, { mode: 'exclusive' }, async () => {
		// Re-read inside the lock — another tab may have just written.
		const inLock = localStorage.getItem(STORAGE_KEY);
		if (inLock) return inLock;
		return generateAndStore();
	}) as Promise<string>;
}

function generateAndStore(): string {
	const id = crypto.randomUUID();
	localStorage.setItem(STORAGE_KEY, id);
	return id;
}

/**
 * Test-only helper. Clears the localStorage entry so subsequent
 * `getUserId()` calls follow the fresh-bootstrap path.
 */
export function _resetForTesting(): void {
	localStorage.removeItem(STORAGE_KEY);
}
