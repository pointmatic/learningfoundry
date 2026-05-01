// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from 'vitest';
import { curriculumTotals } from './progress-dashboard.helpers.js';
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
