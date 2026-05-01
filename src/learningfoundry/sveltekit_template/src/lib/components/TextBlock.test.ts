// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createViewportTracker } from '$lib/utils/viewport-completion.js';

describe('TextBlock completion (via createViewportTracker, 1 s delay)', () => {
	beforeEach(() => {
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('fires textcomplete after 1 s in viewport', () => {
		const callback = vi.fn();
		const tracker = createViewportTracker(callback, 1000);

		tracker.handleIntersecting();
		expect(callback).not.toHaveBeenCalled();

		vi.advanceTimersByTime(1000);
		expect(callback).toHaveBeenCalledOnce();

		tracker.destroy();
	});

	it('does NOT fire if block leaves viewport before 1 s', () => {
		const callback = vi.fn();
		const tracker = createViewportTracker(callback, 1000);

		tracker.handleIntersecting();
		vi.advanceTimersByTime(500);
		tracker.handleNotIntersecting();
		vi.advanceTimersByTime(1000);

		expect(callback).not.toHaveBeenCalled();

		tracker.destroy();
	});

	it('fires on first qualifying viewport interval only (no double-fire)', () => {
		const callback = vi.fn();
		const tracker = createViewportTracker(callback, 1000);

		// First qualifying interval
		tracker.handleIntersecting();
		vi.advanceTimersByTime(1000);
		expect(callback).toHaveBeenCalledOnce();

		// Subsequent intervals should not fire again
		tracker.handleNotIntersecting();
		tracker.handleIntersecting();
		vi.advanceTimersByTime(1000);
		expect(callback).toHaveBeenCalledOnce();

		expect(tracker.fired).toBe(true);
		tracker.destroy();
	});

	it('restarts timer when re-entering viewport after leaving', () => {
		const callback = vi.fn();
		const tracker = createViewportTracker(callback, 1000);

		tracker.handleIntersecting();
		vi.advanceTimersByTime(800);
		tracker.handleNotIntersecting();

		// Re-enter: full 1s needed again
		tracker.handleIntersecting();
		vi.advanceTimersByTime(999);
		expect(callback).not.toHaveBeenCalled();
		vi.advanceTimersByTime(1);
		expect(callback).toHaveBeenCalledOnce();

		tracker.destroy();
	});
});
