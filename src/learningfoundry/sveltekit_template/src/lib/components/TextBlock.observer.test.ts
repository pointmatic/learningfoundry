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
// stubs `IntersectionObserver` to capture the observed element and the
// runtime callback, and asserts both the markup invariants and the
// callback path the observer would actually drive at runtime
// (Story I.t — the regression case the helper-style timer tests can't
// reach because they bypass the component's own observer setup).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import TextBlock from './TextBlock.svelte';

interface CapturedObserver {
	target: Element | null;
	callback: IntersectionObserverCallback | null;
	instance: IntersectionObserver | null;
}

function stubIntersectionObserver(): CapturedObserver {
	const captured: CapturedObserver = { target: null, callback: null, instance: null };
	class FakeObserver {
		constructor(cb: IntersectionObserverCallback) {
			captured.callback = cb;
			captured.instance = this as unknown as IntersectionObserver;
		}
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

function fire(captured: CapturedObserver, isIntersecting: boolean): void {
	if (!captured.callback || !captured.target || !captured.instance) {
		throw new Error('IntersectionObserver was not constructed/observed');
	}
	const entry = {
		isIntersecting,
		target: captured.target,
		intersectionRatio: isIntersecting ? 1 : 0,
		boundingClientRect: {} as DOMRectReadOnly,
		intersectionRect: {} as DOMRectReadOnly,
		rootBounds: null,
		time: 0
	} as IntersectionObserverEntry;
	captured.callback([entry], captured.instance);
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

// ---------------------------------------------------------------------------
// Story I.t — drive the captured IntersectionObserver callback directly so
// the test exercises the runtime branch the browser would actually take.
// The helper-style `createViewportTracker` cases in `TextBlock.test.ts` cover
// the same timer/debounce contract in isolation, but they can't catch a
// regression where the component wires the wrong callback or misses the
// `isIntersecting` toggle path. These two cases close that gap.
// ---------------------------------------------------------------------------

describe('TextBlock IntersectionObserver callback drives ontextcomplete', () => {
	let captured: CapturedObserver;

	beforeEach(() => {
		vi.useFakeTimers();
		captured = stubIntersectionObserver();
	});

	afterEach(() => {
		vi.useRealTimers();
		vi.unstubAllGlobals();
	});

	it('isIntersecting=true for 1 s fires ontextcomplete exactly once', () => {
		const ontextcomplete = vi.fn();
		render(TextBlock, {
			props: {
				content: { markdown: 'Body text.', path: 'fake/path.md' },
				ontextcomplete
			}
		});

		fire(captured, true);
		expect(ontextcomplete).not.toHaveBeenCalled();

		vi.advanceTimersByTime(999);
		expect(ontextcomplete).not.toHaveBeenCalled();

		vi.advanceTimersByTime(1);
		expect(ontextcomplete).toHaveBeenCalledTimes(1);

		// A subsequent re-entry must not fire again — the `fired` latch is
		// what keeps `markLessonComplete` from being called twice for the
		// same block.
		fire(captured, false);
		fire(captured, true);
		vi.advanceTimersByTime(2000);
		expect(ontextcomplete).toHaveBeenCalledTimes(1);
	});

	it('early leave (isIntersecting flips false before 1 s) cancels the fire', () => {
		const ontextcomplete = vi.fn();
		render(TextBlock, {
			props: {
				content: { markdown: 'Body text.', path: 'fake/path.md' },
				ontextcomplete
			}
		});

		fire(captured, true);
		vi.advanceTimersByTime(500);
		fire(captured, false);
		vi.advanceTimersByTime(2000);

		expect(ontextcomplete).not.toHaveBeenCalled();
	});
});
