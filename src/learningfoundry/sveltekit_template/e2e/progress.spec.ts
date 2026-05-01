// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// FR-P9 regression: progress reactivity. Reaching a lesson page must mark
// it `in_progress` and the sidebar status icon must reflect that on the
// next sidebar render — without a page reload.
import { expect, test } from '@playwright/test';

test.describe('progress reactivity', () => {
	test('navigating into a lesson marks it in_progress in the sidebar', async ({ page }) => {
		await page.goto('/');

		// Expand the first module and click into its first lesson.
		await page.locator('aside nav button').first().click();
		await page.locator('aside nav ul ul button').first().click();
		await expect(page).toHaveURL(/\/[^/]+\/[^/]+$/);

		// Sidebar status icons: ○ = not_started, … = in_progress, ✓ = complete.
		// After landing on the lesson page, the active row should not still
		// show ○ (regression check; the previous bug left status forever ○).
		const activeIcon = page.locator('aside nav ul ul button.bg-blue-100 span').first();
		await expect(activeIcon).not.toHaveText('○');
	});
});
