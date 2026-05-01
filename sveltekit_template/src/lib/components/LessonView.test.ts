// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { contentBlockKey, createBlockTracker } from './lesson-view.helpers.js';
import type { ContentBlock } from '$lib/types/index.js';

// ---------------------------------------------------------------------------
// FR-P15 / Story I.p — lifecycle ordering re-instated under Story I.q's
// real-mount harness. Verifies that on mount, `markLessonOpened` resolves
// before `onlessonopen` fires (the contract that lets future telemetry
// adapters trust event order). Other lifecycle cases from I.p remain
// covered by the e2e harness.
// ---------------------------------------------------------------------------

const { markLessonOpenedMock, markLessonInProgressMock, getLessonProgressMock } = vi.hoisted(
	() => ({
		markLessonOpenedMock: vi.fn().mockResolvedValue(undefined),
		markLessonInProgressMock: vi.fn().mockResolvedValue(undefined),
		getLessonProgressMock: vi.fn().mockResolvedValue(null)
	})
);

vi.mock('$lib/db/index.js', () => ({
	markLessonOpened: markLessonOpenedMock,
	markLessonInProgress: markLessonInProgressMock,
	markLessonComplete: vi.fn().mockResolvedValue(undefined),
	getLessonProgress: getLessonProgressMock
}));
// Spread the real curriculum store (so child Navigation gets
// `nextLesson`/`previousLesson`/`navigateTo`) and override only the
// `curriculum` readable to skip its real network fetch.
vi.mock('$lib/stores/curriculum.js', async (importOriginal) => {
	const actual = await importOriginal<typeof import('$lib/stores/curriculum.js')>();
	return {
		...actual,
		curriculum: { subscribe: (fn: (v: null) => void) => (fn(null), () => {}) }
	};
});
vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
vi.mock('$lib/stores/progress.js', () => ({
	invalidateProgress: vi.fn().mockResolvedValue(undefined)
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

describe('LessonView lifecycle ordering on mount (Story I.p, re-instated under Story I.q)', () => {
	beforeEach(() => {
		markLessonOpenedMock.mockClear();
		markLessonInProgressMock.mockClear();
		getLessonProgressMock.mockClear();
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
		await new Promise((r) => setTimeout(r, 0));
		await new Promise((r) => setTimeout(r, 0));

		expect(markLessonOpenedMock).toHaveBeenCalledWith('mod-01', 'lesson-01');
		expect(onlessonopen).toHaveBeenCalledWith({
			moduleId: 'mod-01',
			lessonId: 'lesson-01'
		});
		expect(callOrder).toEqual(['markLessonOpened-resolved', 'onlessonopen']);
	});
});
