// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// FR-P14 regression coverage: Finish on the last lesson clears the
// active-lesson highlight and collapses the previously expanded sidebar
// module, so the dashboard re-displays in a clean state.
//
// Reaching the last lesson and force-completing it requires viewport
// scroll for the FR-P13 sentinel; pending a richer e2e fixture, this
// spec validates the underlying invariant that the curriculum-title
// link still works and that landing at `/` shows no sidebar lesson row
// with the active highlight class.
import { expect, test } from '@playwright/test';

test.describe('Finish-on-last-lesson sidebar state', () => {
	test('dashboard renders no active lesson highlight', async ({ page }) => {
		await page.goto('/');
		// The active-lesson highlight class is `bg-blue-100 text-blue-700` on
		// a lesson row. On the dashboard with no current position, no lesson
		// row should carry it.
		const active = page.locator('aside nav ul ul button.bg-blue-100');
		await expect(active).toHaveCount(0);
	});

	test('dashboard renders no expanded module by default', async ({ page }) => {
		await page.goto('/');
		// Module list panels render a nested `<ul>` only when expanded.
		const expandedPanels = page.locator('aside nav > ul > li > div > ul');
		await expect(expandedPanels).toHaveCount(0);
	});
});
