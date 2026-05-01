// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from 'vitest';
import { contentBlockKey, createBlockTracker } from './lesson-view.helpers.js';
import type { ContentBlock } from '$lib/types/index.js';

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
