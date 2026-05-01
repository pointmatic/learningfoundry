// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from 'vitest';
import { hasAnyProgress } from './progress.js';
import type { LessonProgress, LessonStatus, ModuleProgress } from '$lib/types/index.js';

function makeLessonProgress(
	moduleId: string,
	lessonId: string,
	status: LessonStatus
): LessonProgress {
	return { moduleId, lessonId, status, completedAt: null };
}

function makeModuleProgress(
	moduleId: string,
	lessons: Record<string, LessonStatus>
): ModuleProgress {
	const lessonMap: Record<string, LessonProgress> = {};
	for (const [lessonId, status] of Object.entries(lessons)) {
		lessonMap[lessonId] = makeLessonProgress(moduleId, lessonId, status);
	}
	return {
		moduleId,
		status: 'not_started',
		lessons: lessonMap,
		preAssessment: null,
		postAssessment: null
	};
}

describe('hasAnyProgress', () => {
	it('returns false for an empty store', () => {
		expect(hasAnyProgress({})).toBe(false);
	});

	it('returns false when every lesson is not_started', () => {
		const store = {
			'mod-01': makeModuleProgress('mod-01', { 'lesson-01': 'not_started' }),
			'mod-02': makeModuleProgress('mod-02', {
				'lesson-01': 'not_started',
				'lesson-02': 'not_started'
			})
		};
		expect(hasAnyProgress(store)).toBe(false);
	});

	it('returns true with one in_progress lesson', () => {
		const store = {
			'mod-01': makeModuleProgress('mod-01', {
				'lesson-01': 'not_started',
				'lesson-02': 'in_progress'
			})
		};
		expect(hasAnyProgress(store)).toBe(true);
	});

	it('returns true with one complete lesson', () => {
		const store = {
			'mod-01': makeModuleProgress('mod-01', { 'lesson-01': 'complete' })
		};
		expect(hasAnyProgress(store)).toBe(true);
	});

	it('returns true with one optional lesson that has been touched', () => {
		const store = {
			'mod-01': makeModuleProgress('mod-01', { 'lesson-01': 'optional' })
		};
		expect(hasAnyProgress(store)).toBe(true);
	});

	it('returns true with one opened lesson among otherwise not_started (Story I.p)', () => {
		const store = {
			'mod-01': makeModuleProgress('mod-01', {
				'lesson-01': 'opened',
				'lesson-02': 'not_started'
			})
		};
		expect(hasAnyProgress(store)).toBe(true);
	});
});
