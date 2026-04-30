// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import type { AfterNavigate } from '@sveltejs/kit';
import { describe, expect, it } from 'vitest';
import { resetMainScrollOnForwardNav } from './layout.scroll.js';

/**
 * Build a minimal `AfterNavigate` payload with the fields our helper
 * actually inspects. We cast through `unknown` so we don't have to fake
 * the rest of the rich SvelteKit type (URL, complete-of, route, params).
 */
function makeNav(type: AfterNavigate['type']): AfterNavigate {
	return { type } as unknown as AfterNavigate;
}

describe('resetMainScrollOnForwardNav', () => {
	it('resets scrollTop to 0 on link navigation', () => {
		const el = { scrollTop: 1234 } as HTMLElement;
		resetMainScrollOnForwardNav(makeNav('link'), el);
		expect(el.scrollTop).toBe(0);
	});

	it('resets scrollTop to 0 on goto() navigation', () => {
		const el = { scrollTop: 9000 } as HTMLElement;
		resetMainScrollOnForwardNav(makeNav('goto'), el);
		expect(el.scrollTop).toBe(0);
	});

	it('resets scrollTop to 0 on form navigation', () => {
		const el = { scrollTop: 500 } as HTMLElement;
		resetMainScrollOnForwardNav(makeNav('form'), el);
		expect(el.scrollTop).toBe(0);
	});

	it('leaves scrollTop alone on popstate (back/forward)', () => {
		// Browser handles its own scroll restoration on history navigation —
		// resetting here would clobber that UX.
		const el = { scrollTop: 800 } as HTMLElement;
		resetMainScrollOnForwardNav(makeNav('popstate'), el);
		expect(el.scrollTop).toBe(800);
	});

	it('is a no-op when the element ref is undefined', () => {
		// The bound ref can be undefined during the first navigation
		// before the layout has mounted. Must not throw.
		expect(() =>
			resetMainScrollOnForwardNav(makeNav('link'), undefined)
		).not.toThrow();
	});
});
