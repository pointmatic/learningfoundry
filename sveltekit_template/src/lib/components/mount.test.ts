// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// Smoke check that the Svelte 5 + vitest mount pipeline works end-to-end:
// `vite.config.ts` must set `resolve.conditions: ['browser']` under the
// `process.env.VITEST` guard, and `@testing-library/svelte` must be a
// dev dependency. If either silently reverts (e.g. a future
// "simplify" strips the conditions block), this test fails first —
// before downstream component tests fail with confusing
// `lifecycle_function_unavailable` errors. Story I.q.
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/svelte';
import ProgressBar from './ProgressBar.svelte';

describe('Svelte 5 mount smoke (Story I.q)', () => {
	it('mounts a leaf component and renders the expected DOM', () => {
		const { container } = render(ProgressBar, {
			props: { percent: 42, label: 'Mount smoke' }
		});
		const bar = container.querySelector('[role="progressbar"]') as HTMLElement | null;
		expect(bar).not.toBeNull();
		expect(bar!.getAttribute('aria-valuenow')).toBe('42');
		expect(container.textContent).toContain('Mount smoke');
		expect(container.textContent).toContain('42%');
	});
});
