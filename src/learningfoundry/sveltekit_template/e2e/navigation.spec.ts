// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// FR-P9 regression coverage: in-app navigation must update the URL.
// Before v0.46.0 the sidebar / Next button updated `currentPosition` but
// not the route, so `LessonView` was never re-mounted on lesson change.
import { expect, test } from '@playwright/test';

test.describe('lesson navigation routing', () => {
	test('sidebar lesson click updates URL', async ({ page }) => {
		await page.goto('/');
		// Open the first module by clicking its header in the sidebar.
		const firstModuleHeader = page.locator('aside nav button').first();
		await firstModuleHeader.click();

		// Click the first lesson row in the now-expanded module.
		const firstLessonRow = page.locator('aside nav ul ul button').first();
		await firstLessonRow.click();

		// URL must reflect the click; before v0.46.0 it stayed at "/".
		await expect(page).toHaveURL(/\/[^/]+\/[^/]+$/);
	});

	test('dashboard "Start module" deep-links into a lesson', async ({ page }) => {
		await page.goto('/');
		const startBtn = page.getByRole('button', { name: /start module|continue/i }).first();
		await startBtn.click();
		await expect(page).toHaveURL(/\/[^/]+\/[^/]+$/);
	});
});
