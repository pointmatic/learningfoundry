// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from 'vitest';
import { curriculumTotals, moduleStatus } from './progress-dashboard.helpers.js';
import type { Module, ModuleProgress, LessonProgress } from '$lib/types/index.js';

function makeModule(id: string, lessonCount: number): Module {
	return {
		id,
		title: id,
		description: '',
		pre_assessment: null,
		post_assessment: null,
		lessons: Array.from({ length: lessonCount }, (_, i) => ({
			id: `lesson-${String(i + 1).padStart(2, '0')}`,
			title: `L${i + 1}`,
			content_blocks: []
		}))
	};
}

function makeLessonProgress(
	moduleId: string,
	lessonId: string,
	status: LessonProgress['status']
): LessonProgress {
	return { moduleId, lessonId, status, completedAt: null };
}

function makeProgress(
	mod: Module,
	completedCount: number
): ModuleProgress {
	const lessons: Record<string, LessonProgress> = {};
	for (let i = 0; i < mod.lessons.length; i++) {
		const lid = mod.lessons[i].id;
		lessons[lid] = makeLessonProgress(
			mod.id,
			lid,
			i < completedCount ? 'complete' : 'not_started'
		);
	}
	return {
		moduleId: mod.id,
		status: completedCount === mod.lessons.length ? 'complete' : 'not_started',
		lessons,
		preAssessment: null,
		postAssessment: null
	};
}

describe('curriculumTotals (ProgressDashboard)', () => {
	it('bar shows 0% when no lessons complete', () => {
		const m1 = makeModule('mod-01', 4);
		const m2 = makeModule('mod-02', 6);
		const progress = {
			'mod-01': makeProgress(m1, 0),
			'mod-02': makeProgress(m2, 0)
		};

		const result = curriculumTotals([m1, m2], progress);
		expect(result.totalLessons).toBe(10);
		expect(result.totalComplete).toBe(0);
		expect(result.overallPct).toBe(0);
	});

	it('bar shows 50% when half complete', () => {
		const m1 = makeModule('mod-01', 4);
		const m2 = makeModule('mod-02', 6);
		const progress = {
			'mod-01': makeProgress(m1, 4),
			'mod-02': makeProgress(m2, 1)
		};

		const result = curriculumTotals([m1, m2], progress);
		expect(result.totalLessons).toBe(10);
		expect(result.totalComplete).toBe(5);
		expect(result.overallPct).toBe(50);
	});

	it('bar shows 100% when all complete', () => {
		const m1 = makeModule('mod-01', 3);
		const m2 = makeModule('mod-02', 2);
		const progress = {
			'mod-01': makeProgress(m1, 3),
			'mod-02': makeProgress(m2, 2)
		};

		const result = curriculumTotals([m1, m2], progress);
		expect(result.totalLessons).toBe(5);
		expect(result.totalComplete).toBe(5);
		expect(result.overallPct).toBe(100);
	});

	it('label text is correct format', () => {
		const m1 = makeModule('mod-01', 4);
		const progress = { 'mod-01': makeProgress(m1, 2) };

		const { totalComplete, totalLessons } = curriculumTotals([m1], progress);
		const label = `${totalComplete} of ${totalLessons} lessons completed`;
		expect(label).toBe('2 of 4 lessons completed');
	});

	it('handles zero modules gracefully (0%)', () => {
		const result = curriculumTotals([], {});
		expect(result.totalLessons).toBe(0);
		expect(result.totalComplete).toBe(0);
		expect(result.overallPct).toBe(0);
	});

	it('handles missing progress records gracefully', () => {
		const m1 = makeModule('mod-01', 3);
		const result = curriculumTotals([m1], {});
		expect(result.totalLessons).toBe(3);
		expect(result.totalComplete).toBe(0);
		expect(result.overallPct).toBe(0);
	});
});

describe('moduleStatus (Story I.r — "Continue" button regression fix)', () => {
	function progressWith(
		mod: Module,
		statuses: Record<string, LessonProgress['status']>
	): ModuleProgress {
		const lessons: Record<string, LessonProgress> = {};
		for (const lesson of mod.lessons) {
			const status = statuses[lesson.id] ?? 'not_started';
			lessons[lesson.id] = makeLessonProgress(mod.id, lesson.id, status);
		}
		// Mirror the rollup that `getModuleProgress` produces in the DB layer
		// (any non-`not_started` lesson → module-level `in_progress`; all
		// `complete` → `complete`).
		const all = Object.values(lessons);
		const moduleStatus: ModuleProgress['status'] = all.every(
			(l) => l.status === 'complete'
		)
			? 'complete'
			: all.some((l) => l.status !== 'not_started')
				? 'in_progress'
				: 'not_started';
		return {
			moduleId: mod.id,
			status: moduleStatus,
			lessons,
			preAssessment: null,
			postAssessment: null
		};
	}

	it("module with one 'opened' lesson and zero complete → in_progress (Continue →)", () => {
		const m1 = makeModule('mod-01', 3);
		const progress = {
			'mod-01': progressWith(m1, { 'lesson-01': 'opened' })
		};
		expect(moduleStatus(m1, progress)).toBe('in_progress');
	});

	it("module with one 'in_progress' lesson and zero complete → in_progress (Continue →)", () => {
		const m1 = makeModule('mod-01', 3);
		const progress = {
			'mod-01': progressWith(m1, { 'lesson-02': 'in_progress' })
		};
		expect(moduleStatus(m1, progress)).toBe('in_progress');
	});

	it('module with zero touched lessons → not_started (Start module →)', () => {
		const m1 = makeModule('mod-01', 3);
		const progress = { 'mod-01': progressWith(m1, {}) };
		expect(moduleStatus(m1, progress)).toBe('not_started');
	});

	it('module with all lessons complete → complete (✓ Complete badge)', () => {
		const m1 = makeModule('mod-01', 2);
		const progress = {
			'mod-01': progressWith(m1, {
				'lesson-01': 'complete',
				'lesson-02': 'complete'
			})
		};
		expect(moduleStatus(m1, progress)).toBe('complete');
	});
});
