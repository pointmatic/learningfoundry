// Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0
/**
 * Layout scroll behaviour helpers.
 *
 * Extracted from `+layout.svelte` so the navigation reset logic can be
 * unit-tested without mounting the full layout (which depends on stores,
 * IndexedDB, and `$app/navigation`).
 */

import type { AfterNavigate } from '@sveltejs/kit';

/**
 * Reset the main content element's scroll position to the top on every
 * forward navigation. `popstate` (browser back/forward) is left alone so
 * the browser's built-in scroll restoration is preserved for those.
 *
 * The element may be undefined during the initial mount window; we no-op
 * in that case rather than throwing.
 */
export function resetMainScrollOnForwardNav(
	nav: AfterNavigate,
	mainEl: HTMLElement | undefined
): void {
	if (!mainEl) return;
	if (nav.type === 'popstate') return;
	mainEl.scrollTop = 0;
}
