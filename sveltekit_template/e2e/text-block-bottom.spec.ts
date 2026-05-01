// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// FR-P13 regression coverage: a tall text block must not mark its
// lesson complete until the learner scrolls to the end-of-block
// sentinel. We exercise this directly:
//
//   1. Load the lesson; without scrolling, wait long enough that the
//      1 s debounce would have fired several times — assert no `✓`.
//   2. Scroll `<main>` to the bottom; assert `✓` appears within 2 s.
//
// Uses `e2e/fixtures/curriculum.json`'s `mod-01/lesson-02`, which has
// a 200vh spacer so the sentinel is below the fold on initial render.
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

test.describe('TextBlock end-of-block sentinel (tall block)', () => {
	test('tall lesson does not complete without scroll', async ({ page }) => {
		await page.goto('/mod-01/lesson-02');
		// Sidebar must auto-expand mod-01.
		const activeIcon = page.locator('aside nav ul ul button.bg-blue-100 span').first();
		await activeIcon.waitFor({ state: 'visible' });

		// Wait well past the 1 s debounce; without scroll the sentinel
		// stays below the fold and `textcomplete` must not fire.
		await page.waitForTimeout(3000);
		await expect(activeIcon).not.toHaveText('✓');
	});

	test('scrolling <main> to the bottom triggers completion', async ({ page }) => {
		await page.goto('/mod-01/lesson-02');
		const activeIcon = page.locator('aside nav ul ul button.bg-blue-100 span').first();
		await activeIcon.waitFor({ state: 'visible' });

		// Sanity: not yet complete.
		await page.waitForTimeout(500);
		await expect(activeIcon).not.toHaveText('✓');

		// Scroll the inner `<main>` (the lesson content scroll container)
		// to the bottom so the sentinel enters the viewport.
		await page.locator('main').evaluate((el) => el.scrollTo(0, el.scrollHeight));

		// 1 s debounce + observer flush; allow up to 3 s.
		await expect(activeIcon).toHaveText('✓', { timeout: 3000 });
	});
});
