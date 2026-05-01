// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// FR-P15 / Story I.p — lesson lifecycle visual sequence.
//
// The data sequence underneath is:
//   not_started → opened (mount) → in_progress (first block engage) → complete
// The visual sequence the learner sees is:
//   ○ → … → ✓
// — `opened` and `in_progress` deliberately share the `…` icon so the
// learner doesn't get confronted with a "you opened it but didn't engage"
// distinct symbol; the data distinction exists for analytics hooks only.
import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const FIXTURE_DIR = dirname(fileURLToPath(import.meta.url));
const FIXTURE_BODY = readFileSync(resolve(FIXTURE_DIR, 'fixtures/curriculum.json'), 'utf-8');

test.beforeEach(async ({ page }) => {
	await page.route('**/curriculum.json', (route) =>
		route.fulfill({ contentType: 'application/json', body: FIXTURE_BODY })
	);
});

test.describe('lesson lifecycle visual sequence', () => {
	test('○ → … → ✓ across mount + completion', async ({ page }) => {
		await page.goto('/');

		// Pre-navigation: lesson 1 status icon is ○ (not_started).
		await page.locator('aside nav button').first().click();
		const firstLessonIcon = page.locator('aside nav ul ul button span').first();
		await expect(firstLessonIcon).toHaveText('○');

		// Navigate into the lesson — `opened` writes immediately and the
		// progress store invalidates; the active row's icon switches to …
		// (visually merged with in_progress per FR-P15).
		await page.locator('aside nav ul ul button').first().click();
		await expect(page).toHaveURL(/\/mod-01\/lesson-01$/);

		const activeIcon = page.locator('aside nav ul ul button.bg-blue-100 span').first();
		// Allow up to 1 s for the markLessonOpened + invalidateProgress
		// round-trip; visually merged with in_progress.
		await expect(activeIcon).toHaveText('…', { timeout: 1500 });

		// Wait for the short-text-block sentinel to fire (1 s debounce
		// + observer flush) → completion → ✓.
		await expect(activeIcon).toHaveText('✓', { timeout: 5000 });
	});
});
