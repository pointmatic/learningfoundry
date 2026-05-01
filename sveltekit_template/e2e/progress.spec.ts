// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// FR-P9 + FR-P11 regression coverage. Real lesson completion must:
//   1. Mark the lesson `in_progress` on first navigation.
//   2. Mark the lesson `complete` once every block fires its
//      completion event — and reflect that with `✓` in the sidebar
//      WITHOUT a page reload.
//   3. Increment the dashboard's "X of N completed" count.
//   4. Pre-fill the Next/Finish enabled state on revisit.
//
// We use the dedicated `e2e/fixtures/curriculum.json` (see e2e/README.md)
// so completion behavior is decoupled from whatever curriculum the
// smoke pipeline happens to build.
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

test.describe('progress reactivity', () => {
	test('navigating into a lesson marks it in_progress in the sidebar', async ({ page }) => {
		await page.goto('/');

		await page.locator('aside nav button').first().click();
		await page.locator('aside nav ul ul button').first().click();
		await expect(page).toHaveURL(/\/[^/]+\/[^/]+$/);

		const activeIcon = page.locator('aside nav ul ul button.bg-blue-100 span').first();
		await expect(activeIcon).not.toHaveText('○');
	});

	test('short text-block lesson completes (sidebar ✓ without reload)', async ({ page }) => {
		await page.goto('/');
		await page.locator('aside nav button').first().click();
		// Click the *first* lesson in the first module — `mod-01/lesson-01`
		// of the fixture is a short text block whose sentinel is in view.
		await page.locator('aside nav ul ul button').first().click();
		await expect(page).toHaveURL(/\/mod-01\/lesson-01$/);

		const activeIcon = page.locator('aside nav ul ul button.bg-blue-100 span').first();
		// Allow up to 5 s for the 1 s sentinel debounce + a generous test
		// budget (CI scheduling jitter can stretch IntersectionObserver).
		await expect(activeIcon).toHaveText('✓', { timeout: 5000 });
	});

	test('completing a lesson increments the dashboard total', async ({ page }) => {
		await page.goto('/');
		const dashLabel = page.getByText(/of \d+ lessons completed/);
		await expect(dashLabel).toContainText(/^0 of \d+/);

		await page.locator('aside nav button').first().click();
		await page.locator('aside nav ul ul button').first().click();
		await expect(page).toHaveURL(/\/mod-01\/lesson-01$/);
		await page
			.locator('aside nav ul ul button.bg-blue-100 span')
			.first()
			.waitFor({ state: 'visible' });

		// Wait for completion, then go home to read the dashboard.
		await expect(
			page.locator('aside nav ul ul button.bg-blue-100 span').first()
		).toHaveText('✓', { timeout: 5000 });

		await page.goto('/');
		await expect(dashLabel).toContainText(/^1 of \d+/);
	});

	test('revisiting a complete lesson pre-fills Next as enabled', async ({ page }) => {
		await page.goto('/');
		await page.locator('aside nav button').first().click();
		await page.locator('aside nav ul ul button').first().click();
		await expect(page).toHaveURL(/\/mod-01\/lesson-01$/);

		// Wait for first-time completion.
		await expect(
			page.locator('aside nav ul ul button.bg-blue-100 span').first()
		).toHaveText('✓', { timeout: 5000 });

		// Navigate away then back.
		await page.locator('aside nav ul ul button').nth(1).click();
		await expect(page).toHaveURL(/\/mod-01\/lesson-02$/);
		await page.locator('aside nav ul ul button').first().click();
		await expect(page).toHaveURL(/\/mod-01\/lesson-01$/);

		// Next/Finish is enabled immediately on revisit (FR-P2 / I.g revisit).
		const nextBtn = page.getByRole('button', { name: /Next|Finish/ });
		await expect(nextBtn).toBeEnabled({ timeout: 1000 });
	});
});
