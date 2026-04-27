// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import type { Curriculum } from '$lib/types/index.js';

// Mock $app/navigation BEFORE importing the module under test so its
// top-level `import { goto }` binds to the mock.
const gotoMock = vi.fn();
vi.mock('$app/navigation', () => ({
	goto: gotoMock
}));

// Two-module fixture covering: same-module advance, cross-module advance,
// final-lesson edge case, and reverse traversal across module boundaries.
const FIXTURE: Curriculum = {
	version: 1,
	title: 'Test Curriculum',
	description: 'For navigation tests',
	modules: [
		{
			id: 'mod-01',
			title: 'Module One',
			description: '',
			pre_assessment: null,
			post_assessment: null,
			lessons: [
				{ id: 'lesson-01', title: 'L1', content_blocks: [] },
				{ id: 'lesson-02', title: 'L2', content_blocks: [] }
			]
		},
		{
			id: 'mod-02',
			title: 'Module Two',
			description: '',
			pre_assessment: null,
			post_assessment: null,
			lessons: [
				{ id: 'lesson-01', title: 'M2L1', content_blocks: [] },
				{ id: 'lesson-02', title: 'M2L2', content_blocks: [] }
			]
		}
	]
} as unknown as Curriculum;

// Stub global fetch so the `curriculum` readable store loads our fixture
// instead of doing a real network call (jsdom has no /curriculum.json).
vi.stubGlobal(
	'fetch',
	vi.fn().mockResolvedValue({
		ok: true,
		status: 200,
		statusText: 'OK',
		json: async () => FIXTURE
	})
);

// Import AFTER vi.mock and vi.stubGlobal so they're applied to the module
// under test on first load.
const {
	curriculum,
	currentPosition,
	navigateTo,
	navigateNext,
	navigatePrev
} = await import('./curriculum.js');

// Wait for the readable store's async loader to resolve and emit the
// fixture. Once `curriculum` has data, the derived `modules` store that
// `navigateNext`/`navigatePrev` consume internally will have data too.
beforeAll(async () => {
	await new Promise<void>((resolve) => {
		const unsub = curriculum.subscribe((c) => {
			if (c) {
				unsub();
				resolve();
			}
		});
	});
});

beforeEach(() => {
	gotoMock.mockClear();
	currentPosition.set(null);
});

describe('navigateTo', () => {
	it('updates currentPosition and calls goto with /{moduleId}/{lessonId}', () => {
		navigateTo('mod-01', 'lesson-01');
		expect(get(currentPosition)).toEqual({ moduleId: 'mod-01', lessonId: 'lesson-01' });
		expect(gotoMock).toHaveBeenCalledTimes(1);
		expect(gotoMock).toHaveBeenCalledWith('/mod-01/lesson-01');
	});
});

describe('navigateNext', () => {
	it('advances to the next lesson within the same module', () => {
		navigateTo('mod-01', 'lesson-01');
		gotoMock.mockClear();

		navigateNext();
		expect(get(currentPosition)).toEqual({ moduleId: 'mod-01', lessonId: 'lesson-02' });
		expect(gotoMock).toHaveBeenCalledWith('/mod-01/lesson-02');
	});

	it('crosses module boundaries to the first lesson of the next module', () => {
		navigateTo('mod-01', 'lesson-02');
		gotoMock.mockClear();

		navigateNext();
		expect(get(currentPosition)).toEqual({ moduleId: 'mod-02', lessonId: 'lesson-01' });
		expect(gotoMock).toHaveBeenCalledWith('/mod-02/lesson-01');
	});

	it('is a no-op past the final lesson', () => {
		navigateTo('mod-02', 'lesson-02');
		gotoMock.mockClear();

		navigateNext();
		expect(get(currentPosition)).toEqual({ moduleId: 'mod-02', lessonId: 'lesson-02' });
		expect(gotoMock).not.toHaveBeenCalled();
	});

	it('is a no-op when currentPosition is null', () => {
		navigateNext();
		expect(get(currentPosition)).toBeNull();
		expect(gotoMock).not.toHaveBeenCalled();
	});
});

describe('navigatePrev', () => {
	it('moves to the previous lesson within the same module', () => {
		navigateTo('mod-01', 'lesson-02');
		gotoMock.mockClear();

		navigatePrev();
		expect(get(currentPosition)).toEqual({ moduleId: 'mod-01', lessonId: 'lesson-01' });
		expect(gotoMock).toHaveBeenCalledWith('/mod-01/lesson-01');
	});

	it('crosses module boundaries backward', () => {
		navigateTo('mod-02', 'lesson-01');
		gotoMock.mockClear();

		navigatePrev();
		expect(get(currentPosition)).toEqual({ moduleId: 'mod-01', lessonId: 'lesson-02' });
		expect(gotoMock).toHaveBeenCalledWith('/mod-01/lesson-02');
	});

	it('is a no-op before the first lesson', () => {
		navigateTo('mod-01', 'lesson-01');
		gotoMock.mockClear();

		navigatePrev();
		expect(get(currentPosition)).toEqual({ moduleId: 'mod-01', lessonId: 'lesson-01' });
		expect(gotoMock).not.toHaveBeenCalled();
	});

	it('is a no-op when currentPosition is null', () => {
		navigatePrev();
		expect(get(currentPosition)).toBeNull();
		expect(gotoMock).not.toHaveBeenCalled();
	});
});
