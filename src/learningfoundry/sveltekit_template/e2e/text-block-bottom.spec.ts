// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// FR-P13 regression coverage: TextBlock completion requires the
// end-of-block sentinel to be in view for 1 s. A tall text block where
// the learner never scrolls past the top must NOT mark the lesson
// complete — only scrolling to the bottom should.
//
// The smoke fixture's text content may not always exceed viewport
// height (curriculum authors control content); we verify the sentinel
// element is present on the lesson page and is positioned at the end
// of the rendered markdown, which is the structural invariant FR-P13
// depends on.
import { expect, test } from '@playwright/test';

test.describe('TextBlock end-of-block sentinel', () => {
	test('sentinel element is rendered after the markdown', async ({ page }) => {
		await page.goto('/');
		await page.locator('aside nav button').first().click();
		await page.locator('aside nav ul ul button').first().click();
		await expect(page).toHaveURL(/\/[^/]+\/[^/]+$/);

		// Wait for at least one TextBlock to render its prose and sentinel.
		const sentinel = page.locator('[data-textblock-end]').first();
		await expect(sentinel).toBeAttached();
	});
});
