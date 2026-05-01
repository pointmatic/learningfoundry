// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from 'vitest';
import { createBlockTracker } from './lesson-view.helpers.js';

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
