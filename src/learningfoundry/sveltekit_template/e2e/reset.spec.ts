// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// FR-P12 regression coverage: Reset course button.
//
// The full round-trip from the story task list (complete a lesson →
// button enables → reset → checkmark gone, % returns to 0, dashboard
// reads "0 of N completed", URL is `/`) requires either a tall scroll
// to satisfy the FR-P13 sentinel or a fixture without that constraint.
// Until the e2e fixture story (FR-P11 fixture file) lands, these tests
// validate the smaller invariants that don't require completion:
//   - The button exists in the DOM at the bottom of the sidebar.
//   - On a fresh load (no progress), it is disabled.
//   - Clicking it while disabled is a no-op (URL unchanged).
import { expect, test } from '@playwright/test';

test.describe('Reset course button', () => {
	test('renders disabled when no progress exists', async ({ page }) => {
		await page.goto('/');
		const btn = page.getByRole('button', { name: /Reset course progress/i });
		await expect(btn).toBeVisible();
		await expect(btn).toBeDisabled();
	});

	test('clicking the disabled button does not navigate', async ({ page }) => {
		await page.goto('/');
		const btn = page.getByRole('button', { name: /Reset course progress/i });
		await btn.click({ force: true }).catch(() => {});
		// Still on the dashboard.
		expect(new URL(page.url()).pathname).toBe('/');
	});
});
