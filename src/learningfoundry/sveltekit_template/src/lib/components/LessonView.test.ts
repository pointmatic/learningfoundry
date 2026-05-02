// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { contentBlockKey, createBlockTracker } from './lesson-view.helpers.js';
import type { ContentBlock } from '$lib/types/index.js';

// ---------------------------------------------------------------------------
// FR-P15 / Story I.p — lifecycle ordering re-instated under Story I.q's
// real-mount harness, then extended in Story I.t with engage / complete /
// revisit-suppression / zero-block coverage. The earlier I.p suite was
// e2e-only because vitest couldn't mount Svelte 5 components; with that
// constraint lifted, the unit layer now owns the FR-P15 transition matrix.
// ---------------------------------------------------------------------------

const {
	markLessonOpenedMock,
	markLessonInProgressMock,
	markLessonCompleteMock,
	getLessonProgressMock,
	invalidateProgressMock
} = vi.hoisted(() => ({
	markLessonOpenedMock: vi.fn().mockResolvedValue(undefined),
	markLessonInProgressMock: vi.fn().mockResolvedValue(undefined),
	markLessonCompleteMock: vi.fn().mockResolvedValue(undefined),
	getLessonProgressMock: vi.fn().mockResolvedValue(null),
	invalidateProgressMock: vi.fn().mockResolvedValue(undefined)
}));

vi.mock('$lib/db/index.js', () => ({
	progressRepo: {
		markLessonOpened: markLessonOpenedMock,
		markLessonInProgress: markLessonInProgressMock,
		markLessonComplete: markLessonCompleteMock,
		getLessonProgress: getLessonProgressMock
	}
}));
// Replace the curriculum module wholesale so subscribing to its derived
// stores does not trigger the real `loadCurriculum()` fetch (which otherwise
// 5-second-stalls each test against the unreachable `/curriculum.json`).
vi.mock('$lib/stores/curriculum.js', () => {
	const noopUnsub = () => {};
	const stubReadable = <T,>(value: T) => ({
		subscribe: (fn: (v: T) => void) => {
			fn(value);
			return noopUnsub;
		}
	});
	const stubWritable = <T,>(value: T) => ({
		subscribe: (fn: (v: T) => void) => {
			fn(value);
			return noopUnsub;
		},
		set: vi.fn(),
		update: vi.fn()
	});
	return {
		curriculum: stubReadable(null),
		currentPosition: stubWritable(null),
		modules: stubReadable([]),
		currentModule: stubReadable(null),
		currentLesson: stubReadable(null),
		lessonSequence: stubReadable([]),
		currentIndex: stubReadable(-1),
		nextLesson: stubReadable(null),
		previousLesson: stubReadable(null),
		navigateTo: vi.fn(),
		navigateNext: vi.fn(),
		navigatePrev: vi.fn()
	};
});
vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
vi.mock('$lib/stores/progress.js', () => ({
	invalidateProgress: invalidateProgressMock
}));

describe('LessonView block tracking (via createBlockTracker)', () => {
	it('all blocks complete → returns true on final markBlockComplete', () => {
		const tracker = createBlockTracker(3);

		expect(tracker.markBlockComplete(0)).toBe(false);
		expect(tracker.markBlockComplete(1)).toBe(false);
		expect(tracker.markBlockComplete(2)).toBe(true);
		expect(tracker.allComplete).toBe(true);
	});

	it('button disabled until all blocks done (allComplete is false)', () => {
		const tracker = createBlockTracker(2);

		expect(tracker.allComplete).toBe(false);
		tracker.markBlockComplete(0);
		expect(tracker.allComplete).toBe(false);
		tracker.markBlockComplete(1);
		expect(tracker.allComplete).toBe(true);
	});

	it('pre-fills set when lesson is already complete (revisit)', () => {
		const tracker = createBlockTracker(5, true);

		// Immediately complete — no engagement required
		expect(tracker.allComplete).toBe(true);
		expect(tracker.completedCount).toBe(5);
		expect(tracker.markBlockComplete(0)).toBe(true);
	});

	it('zero-block lesson is immediately complete', () => {
		const tracker = createBlockTracker(0);

		expect(tracker.allComplete).toBe(true);
		expect(tracker.completedCount).toBe(0);
	});

	it('duplicate markBlockComplete calls are idempotent', () => {
		const tracker = createBlockTracker(2);

		tracker.markBlockComplete(0);
		tracker.markBlockComplete(0);
		expect(tracker.completedCount).toBe(1);
		expect(tracker.allComplete).toBe(false);

		tracker.markBlockComplete(1);
		expect(tracker.allComplete).toBe(true);
	});

	it('completedCount tracks incremental progress', () => {
		const tracker = createBlockTracker(4);

		expect(tracker.completedCount).toBe(0);
		tracker.markBlockComplete(2);
		expect(tracker.completedCount).toBe(1);
		tracker.markBlockComplete(0);
		expect(tracker.completedCount).toBe(2);
		tracker.markBlockComplete(3);
		expect(tracker.completedCount).toBe(3);
		tracker.markBlockComplete(1);
		expect(tracker.completedCount).toBe(4);
		expect(tracker.allComplete).toBe(true);
	});
});

describe('contentBlockKey (FR-P10 stable identity)', () => {
	it('uses ref when present', () => {
		const block = {
			type: 'text',
			source: null,
			ref: 'content/mod-01/lesson-01.md',
			content: { markdown: '', path: '' }
		} as ContentBlock;
		expect(contentBlockKey(block, 0)).toBe('text:content/mod-01/lesson-01.md');
	});

	it('uses content.url for video blocks (no ref)', () => {
		const block = {
			type: 'video',
			source: null,
			ref: null,
			content: { url: 'https://www.youtube.com/watch?v=abc' }
		} as ContentBlock;
		expect(contentBlockKey(block, 0)).toBe('video:https://www.youtube.com/watch?v=abc');
	});

	it('falls back to type + index when neither ref nor url is present', () => {
		const block = {
			type: 'visualization',
			source: null,
			ref: null,
			content: {}
		} as unknown as ContentBlock;
		expect(contentBlockKey(block, 2)).toBe('visualization-2');
	});

	it('two video blocks with different URLs produce different keys', () => {
		const a = {
			type: 'video',
			source: null,
			ref: null,
			content: { url: 'https://youtu.be/AAA' }
		} as ContentBlock;
		const b = {
			type: 'video',
			source: null,
			ref: null,
			content: { url: 'https://youtu.be/BBB' }
		} as ContentBlock;
		expect(contentBlockKey(a, 0)).not.toBe(contentBlockKey(b, 0));
	});
});

// ---------------------------------------------------------------------------
// Lifecycle harness: stub `IntersectionObserver` to capture both the target
// element and the callback so each TextBlock's "1 s in viewport → fire
// ontextcomplete" branch can be driven from the test body. The text-block
// path is the cheapest reliable way to surface a `blockcomplete` event from
// a real LessonView mount; mocking ContentBlock would need a stand-in
// Svelte 5 component, which is more boilerplate than the IO drive-by.
// ---------------------------------------------------------------------------

interface CapturedIO {
	target: Element;
	callback: IntersectionObserverCallback;
	instance: IntersectionObserver;
}

function fireIntersect(captured: CapturedIO, isIntersecting: boolean): void {
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

function makeTextBlock(ref: string) {
	return {
		type: 'text',
		source: null,
		ref,
		content: { markdown: 'Hello world.', path: `${ref}.md` }
	} as ContentBlock;
}

async function flushAsync(): Promise<void> {
	// Drain both microtasks (Promise resolutions inside LessonView.onMount
	// and handleBlockComplete) and any same-tick `setTimeout(_, 0)` chains
	// Svelte's scheduler may queue. Six iterations is empirically more than
	// enough for the deepest mount + blockcomplete chain in this file.
	for (let i = 0; i < 6; i += 1) {
		await Promise.resolve();
	}
}

describe('LessonView lifecycle ordering on mount (Story I.p, re-instated under Story I.q)', () => {
	beforeEach(() => {
		markLessonOpenedMock.mockReset().mockResolvedValue(undefined);
		markLessonInProgressMock.mockReset().mockResolvedValue(undefined);
		markLessonCompleteMock.mockReset().mockResolvedValue(undefined);
		getLessonProgressMock.mockReset().mockResolvedValue(null);
		invalidateProgressMock.mockReset().mockResolvedValue(undefined);
		// Stub IntersectionObserver so child TextBlocks don't blow up.
		class FakeObserver {
			observe() {}
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
	});

	afterEach(() => {
		vi.unstubAllGlobals();
		vi.clearAllMocks();
	});

	it('markLessonOpened resolves before onlessonopen fires', async () => {
		// Lazy-import after mocks are registered so the component picks up
		// the mocked DB module.
		const { render } = await import('@testing-library/svelte');
		const LessonView = (await import('./LessonView.svelte')).default;

		const callOrder: string[] = [];
		// Make markLessonOpened resolve on a microtask boundary so we
		// can verify the component awaits it before dispatching the event.
		markLessonOpenedMock.mockImplementation(async () => {
			await Promise.resolve();
			callOrder.push('markLessonOpened-resolved');
		});

		const onlessonopen = vi.fn(() => {
			callOrder.push('onlessonopen');
		});

		const lesson = {
			id: 'lesson-01',
			title: 'L1',
			content_blocks: [
				{
					type: 'text',
					source: null,
					ref: null,
					content: { markdown: 'hi', path: 'x.md' }
				}
			]
		} as unknown as Parameters<typeof render>[1] extends { props: infer P } ? P : never;

		render(LessonView, {
			props: { lesson, moduleId: 'mod-01', onlessonopen }
		});

		// Allow onMount + the awaited markLessonOpened to settle.
		await flushAsync();

		expect(markLessonOpenedMock).toHaveBeenCalledWith('mod-01', 'lesson-01');
		expect(onlessonopen).toHaveBeenCalledWith({
			moduleId: 'mod-01',
			lessonId: 'lesson-01'
		});
		expect(callOrder).toEqual(['markLessonOpened-resolved', 'onlessonopen']);
	});
});

// ---------------------------------------------------------------------------
// FR-P15 transition matrix (Story I.t)
// ---------------------------------------------------------------------------

describe('LessonView FR-P15 lifecycle transitions (Story I.t)', () => {
	let observers: CapturedIO[];

	beforeEach(() => {
		markLessonOpenedMock.mockReset().mockResolvedValue(undefined);
		markLessonInProgressMock.mockReset().mockResolvedValue(undefined);
		markLessonCompleteMock.mockReset().mockResolvedValue(undefined);
		getLessonProgressMock.mockReset().mockResolvedValue(null);
		invalidateProgressMock.mockReset().mockResolvedValue(undefined);

		observers = [];
		const captured = observers;
		class FakeObserver {
			callback: IntersectionObserverCallback;
			constructor(cb: IntersectionObserverCallback) {
				this.callback = cb;
			}
			observe(el: Element) {
				captured.push({
					target: el,
					callback: this.callback,
					instance: this as unknown as IntersectionObserver
				});
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
		vi.clearAllMocks();
	});

	it('engage transition: first blockcomplete fires markLessonInProgress + onlessonengage', async () => {
		const { render } = await import('@testing-library/svelte');
		const LessonView = (await import('./LessonView.svelte')).default;

		const onlessonopen = vi.fn();
		const onlessonengage = vi.fn();
		const onlessoncomplete = vi.fn();

		const lesson = {
			id: 'lesson-01',
			title: 'L1',
			content_blocks: [makeTextBlock('block-0')]
		};

		render(LessonView, {
			props: {
				lesson: lesson as unknown as never,
				moduleId: 'mod-01',
				onlessonopen,
				onlessonengage,
				onlessoncomplete
			}
		});

		await flushAsync();

		expect(onlessonopen).toHaveBeenCalledWith({ moduleId: 'mod-01', lessonId: 'lesson-01' });
		expect(markLessonInProgressMock).not.toHaveBeenCalled();

		expect(observers.length).toBeGreaterThan(0);
		fireIntersect(observers[0], true);
		vi.advanceTimersByTime(1000);
		await flushAsync();

		expect(markLessonInProgressMock).toHaveBeenCalledWith('mod-01', 'lesson-01');
		expect(onlessonengage).toHaveBeenCalledWith({
			moduleId: 'mod-01',
			lessonId: 'lesson-01'
		});
	});

	it('complete transition: blockcomplete on every block fires markLessonComplete + invalidateProgress + onlessoncomplete', async () => {
		const { render } = await import('@testing-library/svelte');
		const LessonView = (await import('./LessonView.svelte')).default;

		const onlessonengage = vi.fn();
		const onlessoncomplete = vi.fn();

		const lesson = {
			id: 'lesson-02',
			title: 'L2',
			content_blocks: [makeTextBlock('block-0'), makeTextBlock('block-1')]
		};

		render(LessonView, {
			props: {
				lesson: lesson as unknown as never,
				moduleId: 'mod-01',
				onlessonengage,
				onlessoncomplete
			}
		});

		await flushAsync();

		expect(observers.length).toBeGreaterThanOrEqual(2);

		fireIntersect(observers[0], true);
		vi.advanceTimersByTime(1000);
		await flushAsync();

		expect(onlessonengage).toHaveBeenCalledTimes(1);
		expect(markLessonCompleteMock).not.toHaveBeenCalled();

		fireIntersect(observers[1], true);
		vi.advanceTimersByTime(1000);
		await flushAsync();

		expect(markLessonCompleteMock).toHaveBeenCalledWith('mod-01', 'lesson-02');
		// Two-arg signature is fine — the spread mock accepts any payload.
		expect(invalidateProgressMock).toHaveBeenCalled();
		expect(onlessoncomplete).toHaveBeenCalledWith({
			moduleId: 'mod-01',
			lessonId: 'lesson-02'
		});
		// Engage stays at exactly one even after the second block fires —
		// the `engaged` latch is what gates the FR-P15 transition.
		expect(onlessonengage).toHaveBeenCalledTimes(1);
	});

	it('revisit suppression: existing status=complete fires onlessonopen only — no engage / complete', async () => {
		getLessonProgressMock.mockResolvedValue({ status: 'complete' });

		const { render } = await import('@testing-library/svelte');
		const LessonView = (await import('./LessonView.svelte')).default;

		const onlessonopen = vi.fn();
		const onlessonengage = vi.fn();
		const onlessoncomplete = vi.fn();

		const lesson = {
			id: 'lesson-03',
			title: 'L3',
			content_blocks: [makeTextBlock('block-0')]
		};

		render(LessonView, {
			props: {
				lesson: lesson as unknown as never,
				moduleId: 'mod-01',
				onlessonopen,
				onlessonengage,
				onlessoncomplete
			}
		});

		await flushAsync();

		expect(markLessonOpenedMock).toHaveBeenCalledWith('mod-01', 'lesson-03');
		expect(onlessonopen).toHaveBeenCalledTimes(1);

		// Even if a TextBlock fires its observer (e.g. the sentinel is
		// already on-screen on revisit), `handleBlockComplete` short-circuits
		// because `allBlocksComplete` was pre-set in the revisit branch.
		if (observers.length > 0) {
			fireIntersect(observers[0], true);
			vi.advanceTimersByTime(1000);
			await flushAsync();
		}

		expect(markLessonInProgressMock).not.toHaveBeenCalled();
		expect(markLessonCompleteMock).not.toHaveBeenCalled();
		expect(onlessonengage).not.toHaveBeenCalled();
		expect(onlessoncomplete).not.toHaveBeenCalled();
	});

	it('zero-block lesson: onlessonopen → markLessonComplete → onlessoncomplete fire in order with no engage in between', async () => {
		const { render } = await import('@testing-library/svelte');
		const LessonView = (await import('./LessonView.svelte')).default;

		const callOrder: string[] = [];
		markLessonOpenedMock.mockImplementation(async () => {
			callOrder.push('markLessonOpened');
		});
		markLessonCompleteMock.mockImplementation(async () => {
			callOrder.push('markLessonComplete');
		});

		const onlessonopen = vi.fn(() => {
			callOrder.push('onlessonopen');
		});
		const onlessonengage = vi.fn(() => {
			callOrder.push('onlessonengage');
		});
		const onlessoncomplete = vi.fn(() => {
			callOrder.push('onlessoncomplete');
		});

		const lesson = {
			id: 'lesson-zero',
			title: 'Empty',
			content_blocks: []
		};

		render(LessonView, {
			props: {
				lesson: lesson as unknown as never,
				moduleId: 'mod-01',
				onlessonopen,
				onlessonengage,
				onlessoncomplete
			}
		});

		await flushAsync();

		expect(callOrder).toEqual([
			'markLessonOpened',
			'onlessonopen',
			'markLessonComplete',
			'onlessoncomplete'
		]);
		expect(onlessonengage).not.toHaveBeenCalled();
		expect(markLessonInProgressMock).not.toHaveBeenCalled();
	});
});
