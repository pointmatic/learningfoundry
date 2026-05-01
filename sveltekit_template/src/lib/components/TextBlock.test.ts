// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createViewportTracker } from '$lib/utils/viewport-completion.js';

// FR-P13: TextBlock completion observes a sentinel at the end of the
// rendered markdown — completion requires the *bottom* of the block to
// be in view for 1 s, not just any portion. The viewport tracker tested
// here is target-agnostic; the sentinel-vs-wrapper choice is made in
// `TextBlock.svelte` by which element it `observer.observe()`s.

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

	it('tall block: sentinel never intersects → does not fire even after 5 s', () => {
		const callback = vi.fn();
		const tracker = createViewportTracker(callback, 1000);

		// Sentinel at the end of a tall block is never in the viewport.
		// The component never calls `handleIntersecting` for this case.
		vi.advanceTimersByTime(5000);
		expect(callback).not.toHaveBeenCalled();

		tracker.destroy();
	});

	it('tall block: sentinel scrolled into view fires 1 s later', () => {
		const callback = vi.fn();
		const tracker = createViewportTracker(callback, 1000);

		// Initial state: sentinel below the fold. Simulate a scroll that
		// brings the sentinel into the viewport.
		vi.advanceTimersByTime(2000);
		expect(callback).not.toHaveBeenCalled();

		tracker.handleIntersecting();
		vi.advanceTimersByTime(999);
		expect(callback).not.toHaveBeenCalled();
		vi.advanceTimersByTime(1);
		expect(callback).toHaveBeenCalledOnce();

		tracker.destroy();
	});

	it('sentinel briefly visible (<1 s) then hidden → does not fire', () => {
		const callback = vi.fn();
		const tracker = createViewportTracker(callback, 1000);

		tracker.handleIntersecting();
		vi.advanceTimersByTime(700);
		tracker.handleNotIntersecting();
		vi.advanceTimersByTime(2000);

		expect(callback).not.toHaveBeenCalled();
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
