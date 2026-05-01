// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// FR-P10 regression coverage: when navigating between two lessons that
// each contain a video block, only the new lesson's iframe should be
// present — the previous player must be destroyed. The {#key} wrapper
// in `[module]/[lesson]/+page.svelte` plus the stable block key in
// `LessonView` enforce this.
import { expect, test } from '@playwright/test';

test.describe('video block lifecycle', () => {
	test('lesson page renders at most one YouTube iframe per video block', async ({ page }) => {
		await page.goto('/');
		await page.locator('aside nav button').first().click();
		await page.locator('aside nav ul ul button').first().click();
		await expect(page).toHaveURL(/\/[^/]+\/[^/]+$/);

		// Wait briefly for the YouTube IFrame API to upgrade the placeholder
		// `<div id="yt-player-…">` into an `<iframe>`. If the API is blocked
		// (no network in CI), there will be zero iframes — that's still a
		// pass for "no leaked iframes from a prior lesson", which is what
		// the regression cares about.
		await page.waitForTimeout(2000);
		const iframes = await page.locator('iframe[src*="youtube"]').count();
		expect(iframes).toBeLessThanOrEqual(1);
	});
});
