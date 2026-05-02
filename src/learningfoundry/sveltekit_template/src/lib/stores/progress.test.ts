// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import type { Curriculum, ModuleProgress } from '$lib/types/index.js';

// Mock the DB layer so no real IndexedDB/sql.js is needed
const mockGetModuleProgress = vi.fn();
vi.mock('$lib/db/index.js', () => ({
	progressRepo: {
		getModuleProgress: (...args: unknown[]) => mockGetModuleProgress(...args)
	}
}));

const mod = await import('./progress.js');
const progressStore = mod.progressStore as import('svelte/store').Writable<Record<string, ModuleProgress>>;
const invalidateProgress = mod.invalidateProgress as (c: Curriculum | null) => Promise<void>;

const FIXTURE: Curriculum = {
	version: 1,
	title: 'Test',
	description: '',
	modules: [
		{
			id: 'mod-01',
			title: 'M1',
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
			title: 'M2',
			description: '',
			pre_assessment: null,
			post_assessment: null,
			lessons: [{ id: 'lesson-01', title: 'M2L1', content_blocks: [] }]
		}
	]
} as unknown as Curriculum;

function makeMockProgress(moduleId: string): ModuleProgress {
	return {
		moduleId,
		status: 'not_started',
		lessons: {},
		preAssessment: null,
		postAssessment: null
	};
}

beforeEach(() => {
	mockGetModuleProgress.mockReset();
	progressStore.set({});
});

describe('invalidateProgress', () => {
	it('writes fetched data to store', async () => {
		mockGetModuleProgress.mockImplementation((moduleId: string) =>
			Promise.resolve(makeMockProgress(moduleId))
		);

		await invalidateProgress(FIXTURE);

		const result = get(progressStore) as Record<string, ModuleProgress>;
		expect(Object.keys(result)).toEqual(['mod-01', 'mod-02']);
		expect(result['mod-01'].moduleId).toBe('mod-01');
		expect(result['mod-02'].moduleId).toBe('mod-02');
	});

	it('subsequent calls overwrite not append', async () => {
		mockGetModuleProgress.mockImplementation((moduleId: string) =>
			Promise.resolve({ ...makeMockProgress(moduleId), status: 'not_started' as const })
		);
		await invalidateProgress(FIXTURE);
		expect((get(progressStore) as Record<string, ModuleProgress>)['mod-01'].status).toBe('not_started');

		// Second call with updated status
		mockGetModuleProgress.mockImplementation((moduleId: string) =>
			Promise.resolve({ ...makeMockProgress(moduleId), status: 'in_progress' as const })
		);
		await invalidateProgress(FIXTURE);
		expect((get(progressStore) as Record<string, ModuleProgress>)['mod-01'].status).toBe('in_progress');
	});

	it('is a no-op when curriculum is null', async () => {
		mockGetModuleProgress.mockImplementation((moduleId: string) =>
			Promise.resolve(makeMockProgress(moduleId))
		);

		await invalidateProgress(null);

		expect(get(progressStore)).toEqual({});
		expect(mockGetModuleProgress).not.toHaveBeenCalled();
	});
});
