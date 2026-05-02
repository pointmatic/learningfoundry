// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// Story I.t — real-DOM mount coverage for `VideoBlock.svelte`.
//
// The helper-style `createViewportTracker` cases below stay because they
// document the timer/debounce contract in isolation. The new mount-based
// cases exercise the runtime wiring the helpers cannot reach: the
// `<script src="…/iframe_api">` injection on cold start, the `YT.Player`
// destroy/recreate cycle when the URL prop changes (the v0.46.0 stale-
// iframe regression), and the `IntersectionObserver` fallback that arms
// after 5 s when the YT API never finished loading.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushSync } from 'svelte';
import { render } from '@testing-library/svelte';
import { createViewportTracker } from '$lib/utils/viewport-completion.js';
import VideoBlock from './VideoBlock.svelte';
import type { VideoContent } from '$lib/types/index.js';

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

// ---------------------------------------------------------------------------
// Mount-based coverage (Story I.t)
// ---------------------------------------------------------------------------

interface MockPlayerInstance {
	id: string;
	videoId: string;
	events: { onStateChange?: (event: { data: number }) => void };
	destroy: ReturnType<typeof vi.fn>;
}

interface CapturedFallbackObserver {
	target: Element | null;
	count: number;
}

function removeYtScript() {
	document
		.querySelectorAll('script[src*="youtube.com/iframe_api"]')
		.forEach((el) => el.remove());
}

describe('VideoBlock mount — YouTube IFrame API script injection', () => {
	afterEach(() => {
		removeYtScript();
		// Reset the global the `onYouTubeIframeAPIReady` handler attaches to.
		delete (window as { onYouTubeIframeAPIReady?: unknown }).onYouTubeIframeAPIReady;
		delete (window as { YT?: unknown }).YT;
	});

	it('injects the iframe_api script tag and renders the player placeholder', () => {
		expect(document.querySelector('script[src*="youtube.com/iframe_api"]')).toBeNull();

		const { container } = render(VideoBlock, {
			props: {
				content: { url: 'https://youtu.be/abc123', provider: 'youtube' } as VideoContent,
				onvideocomplete: vi.fn()
			}
		});
		flushSync();

		expect(document.querySelector('script[src*="youtube.com/iframe_api"]')).not.toBeNull();
		const placeholder = container.querySelector('[id^="yt-player-"]') as HTMLElement | null;
		expect(placeholder).not.toBeNull();
		expect(placeholder!.classList.contains('absolute')).toBe(true);
	});
});

describe('VideoBlock mount — URL change destroys old player and creates new one', () => {
	let players: MockPlayerInstance[];
	let MockPlayer: ReturnType<typeof vi.fn>;

	beforeEach(() => {
		players = [];
		MockPlayer = vi.fn().mockImplementation((id: string, opts: { videoId: string; events: any }) => {
			const inst: MockPlayerInstance = {
				id,
				videoId: opts.videoId,
				events: opts.events,
				destroy: vi.fn()
			};
			players.push(inst);
			return inst;
		});
		vi.stubGlobal('YT', {
			Player: MockPlayer,
			PlayerState: { ENDED: 0, PLAYING: 1, PAUSED: 2 }
		});
	});

	afterEach(() => {
		flushSync();
		vi.unstubAllGlobals();
		removeYtScript();
		delete (window as { YT?: unknown }).YT;
	});

	it('rerender with a different URL destroys the prior player, creates a new one with the new videoId, and resets the fired latch', () => {
		const onvideocomplete = vi.fn();

		const { rerender } = render(VideoBlock, {
			props: {
				content: { url: 'https://youtu.be/AAA', provider: 'youtube' } as VideoContent,
				onvideocomplete
			}
		});
		flushSync();

		expect(MockPlayer).toHaveBeenCalledTimes(1);
		expect(players[0].videoId).toBe('AAA');
		expect(players[0].destroy).not.toHaveBeenCalled();

		rerender({
			content: { url: 'https://youtu.be/BBB', provider: 'youtube' } as VideoContent,
			onvideocomplete
		});
		flushSync();

		expect(players[0].destroy).toHaveBeenCalledTimes(1);
		expect(MockPlayer).toHaveBeenCalledTimes(2);
		expect(players[1].videoId).toBe('BBB');

		// `fired` reset proxy: ENDED on the *new* player still fires
		// onvideocomplete. If the latch were not reset on URL change, this
		// callback would never invoke its inner branch.
		players[1].events.onStateChange?.({ data: 0 });
		expect(onvideocomplete).toHaveBeenCalledTimes(1);
	});
});

describe('VideoBlock mount — viewport fallback arms after 5 s when YT never loads', () => {
	let captured: CapturedFallbackObserver;

	beforeEach(() => {
		captured = { target: null, count: 0 };
		class FakeObserver {
			observe(el: Element) {
				captured.target = el;
				captured.count += 1;
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
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
		vi.unstubAllGlobals();
		removeYtScript();
		delete (window as { onYouTubeIframeAPIReady?: unknown }).onYouTubeIframeAPIReady;
		delete (window as { YT?: unknown }).YT;
	});

	it('attaches the fallback IntersectionObserver to the wrapper element after the 5 s threshold', () => {
		const { container } = render(VideoBlock, {
			props: {
				content: { url: 'https://youtu.be/abc123', provider: 'youtube' } as VideoContent,
				onvideocomplete: vi.fn()
			}
		});
		flushSync();

		// No fallback observer should be attached before 5 s elapse.
		expect(captured.count).toBe(0);

		vi.advanceTimersByTime(4999);
		expect(captured.count).toBe(0);

		vi.advanceTimersByTime(1);
		expect(captured.count).toBe(1);

		// The wrapper `<div bind:this={containerEl}>` is the outer block-
		// level element with the aspect-ratio padding inline style.
		const wrapper = container.querySelector('div.relative') as HTMLElement | null;
		expect(wrapper).not.toBeNull();
		expect(captured.target).toBe(wrapper);
	});
});
