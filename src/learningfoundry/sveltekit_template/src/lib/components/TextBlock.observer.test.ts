// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// Real-DOM coverage for `TextBlock.svelte` — guards against the v0.48.0
// regression where the end-of-block sentinel had `height: 0`, causing
// `IntersectionObserver`'s `intersectionRatio` to degenerate to zero
// against the configured `0.1` threshold and the `isIntersecting`
// branch to never fire (no `textcomplete` → no `markLessonComplete` →
// no progress at all).
//
// Mounts the component via `@testing-library/svelte` (enabled by the
// `resolve.conditions: ['browser']` vite-config addition in Story I.q),
// stubs `IntersectionObserver` to capture the observed element, and
// asserts the captured element is the sentinel and carries a non-zero
// inline height.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import TextBlock from './TextBlock.svelte';

interface CapturedObserver {
	target: Element | null;
}

function stubIntersectionObserver(): CapturedObserver {
	const captured: CapturedObserver = { target: null };
	class FakeObserver {
		observe(el: Element) {
			captured.target = el;
		}
		unobserve() {}
		disconnect() {}
		takeRecords() {
			return [];
		}
	}
	vi.stubGlobal(
		'IntersectionObserver',
		FakeObserver as unknown as typeof IntersectionObserver
	);
	return captured;
}

describe('TextBlock real-DOM IntersectionObserver target', () => {
	let captured: CapturedObserver;

	beforeEach(() => {
		captured = stubIntersectionObserver();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('observes the end-of-block sentinel, not the wrapper', () => {
		render(TextBlock, {
			props: {
				content: { markdown: '# Hello\n\nBody text.', path: 'fake/path.md' },
				ontextcomplete: () => {}
			}
		});
		expect(captured.target).not.toBeNull();
		expect((captured.target as HTMLElement).hasAttribute('data-textblock-end')).toBe(true);
	});

	it('observed sentinel has non-zero inline height (anti-regression)', () => {
		render(TextBlock, {
			props: {
				content: { markdown: 'Just some prose.', path: 'fake/path.md' },
				ontextcomplete: () => {}
			}
		});
		const el = captured.target as HTMLElement;
		expect(el).not.toBeNull();
		// jsdom doesn't lay out, so `getBoundingClientRect()` is unreliable;
		// the inline `style.height` is what the browser reads at runtime to
		// give the observer a non-degenerate ratio.
		expect(el.style.height).toBe('1px');
	});

	it('does not observe the prose wrapper directly', () => {
		render(TextBlock, {
			props: {
				content: { markdown: 'Some prose.', path: 'fake/path.md' },
				ontextcomplete: () => {}
			}
		});
		const el = captured.target as HTMLElement;
		expect(el).not.toBeNull();
		// The wrapper (`<div class="prose ...">`) does NOT carry the
		// sentinel marker, so observing it would slip past this assertion.
		expect(el.classList.contains('prose')).toBe(false);
	});
});
