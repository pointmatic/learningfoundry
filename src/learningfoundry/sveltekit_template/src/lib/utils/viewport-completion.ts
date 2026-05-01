// Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0
/**
 * Viewport-based completion tracker.
 *
 * Shared logic extracted from `TextBlock.svelte` and `VideoBlock.svelte` so
 * the IntersectionObserver + debounce-timer pattern can be unit-tested
 * without mounting Svelte components.
 */

export interface ViewportTracker {
	/** Simulate the element entering the viewport. */
	handleIntersecting(): void;
	/** Simulate the element leaving the viewport. */
	handleNotIntersecting(): void;
	/** Clean up timers. */
	destroy(): void;
	/** Whether the completion callback has already fired. */
	readonly fired: boolean;
}

/**
 * Create a viewport completion tracker that calls `callback` after the
 * element has been continuously in the viewport for `delayMs` milliseconds.
 *
 * - Fires at most once (guard against double-fire).
 * - Cancels the timer if the element leaves the viewport before the delay.
 */
export function createViewportTracker(
	callback: () => void,
	delayMs: number
): ViewportTracker {
	let fired = false;
	let timer: ReturnType<typeof setTimeout> | null = null;

	return {
		handleIntersecting() {
			if (fired) return;
			timer = setTimeout(() => {
				if (!fired) {
					fired = true;
					callback();
				}
			}, delayMs);
		},

		handleNotIntersecting() {
			if (timer !== null) {
				clearTimeout(timer);
				timer = null;
			}
		},

		destroy() {
			if (timer !== null) {
				clearTimeout(timer);
				timer = null;
			}
		},

		get fired() {
			return fired;
		}
	};
}
