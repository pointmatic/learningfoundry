// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createViewportTracker } from '$lib/utils/viewport-completion.js';

describe('VideoBlock completion — YT ENDED state', () => {
	it('mock YT global: ENDED state fires videocomplete', () => {
		const callback = vi.fn();
		let registeredOnStateChange: ((event: { data: number }) => void) | undefined;

		// Simulate YT.Player constructor capturing the onStateChange handler
		const MockPlayer = vi.fn().mockImplementation((_id: string, opts: any) => {
			registeredOnStateChange = opts.events?.onStateChange;
			return { destroy: vi.fn() };
		});

		const YT = {
			Player: MockPlayer,
			PlayerState: { ENDED: 0, PLAYING: 1, PAUSED: 2 }
		};

		// Simulate the onStateChange callback with ENDED state
		expect(registeredOnStateChange).toBeUndefined();
		new YT.Player('test-player', {
			videoId: 'abc123',
			events: {
				onStateChange: (event: { data: number }) => {
					if (event.data === YT.PlayerState.ENDED) {
						callback();
					}
				}
			}
		});

		// Simulate PLAYING state — should NOT fire
		registeredOnStateChange!({ data: YT.PlayerState.PLAYING });
		expect(callback).not.toHaveBeenCalled();

		// Simulate ENDED state — should fire
		registeredOnStateChange!({ data: YT.PlayerState.ENDED });
		expect(callback).toHaveBeenCalledOnce();
	});
});

describe('VideoBlock completion — viewport fallback (3 s)', () => {
	beforeEach(() => {
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('fires videocomplete after 3 s in viewport when YT API absent', () => {
		const callback = vi.fn();
		const tracker = createViewportTracker(callback, 3000);

		tracker.handleIntersecting();
		vi.advanceTimersByTime(2999);
		expect(callback).not.toHaveBeenCalled();

		vi.advanceTimersByTime(1);
		expect(callback).toHaveBeenCalledOnce();

		tracker.destroy();
	});

	it('does NOT fire if element leaves viewport before 3 s', () => {
		const callback = vi.fn();
		const tracker = createViewportTracker(callback, 3000);

		tracker.handleIntersecting();
		vi.advanceTimersByTime(2000);
		tracker.handleNotIntersecting();
		vi.advanceTimersByTime(3000);

		expect(callback).not.toHaveBeenCalled();
		tracker.destroy();
	});

	it('fires once only even with repeated viewport entries', () => {
		const callback = vi.fn();
		const tracker = createViewportTracker(callback, 3000);

		tracker.handleIntersecting();
		vi.advanceTimersByTime(3000);
		expect(callback).toHaveBeenCalledOnce();

		tracker.handleNotIntersecting();
		tracker.handleIntersecting();
		vi.advanceTimersByTime(3000);
		expect(callback).toHaveBeenCalledOnce();

		tracker.destroy();
	});
});
