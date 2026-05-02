// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { curriculumTotals, moduleStatus } from './progress-dashboard.helpers.js';
import type { Module, ModuleProgress, LessonProgress } from '$lib/types/index.js';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

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

// ---------------------------------------------------------------------------
// Story I.u — real-DOM mount coverage. The helper cases above pin the math
// and rollup logic; the cases below pin how those numbers reach the user:
// the per-module ProgressBar `width` style, the `{#if totalLessons > 0}`
// gate on the curriculum summary bar, and the per-module action button vs
// "✓ Complete" badge depending on rollup status.
// ---------------------------------------------------------------------------

describe('ProgressDashboard mount — per-module ProgressBar widths', () => {
	let ProgressDashboard: typeof import('./ProgressDashboard.svelte').default;

	beforeEach(async () => {
		ProgressDashboard = (await import('./ProgressDashboard.svelte')).default;
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('three modules with mixed progress → each card renders <ProgressBar> with the expected percent in inline style', async () => {
		const m1 = makeModule('mod-01', 4); // 100%
		const m2 = makeModule('mod-02', 4); // 50%
		const m3 = makeModule('mod-03', 4); // 0%
		const progress = {
			'mod-01': makeProgress(m1, 4),
			'mod-02': makeProgress(m2, 2),
			'mod-03': makeProgress(m3, 0)
		};

		const { render } = await import('@testing-library/svelte');
		const { container } = render(ProgressDashboard, {
			props: { modules: [m1, m2, m3], progress }
		});

		// Each module card has its own ProgressBar; the curriculum-summary
		// bar at the top brings the total to 4 progressbars.
		const bars = container.querySelectorAll('[role="progressbar"]');
		expect(bars.length).toBe(4);

		const widthOf = (el: Element): number => {
			const style = (el as HTMLElement).style.width;
			// `style.width` parses as e.g. "75%" — strip and coerce.
			return Number(style.replace('%', ''));
		};

		// bars[0] is the curriculum summary (50%); bars[1..3] are per-module.
		expect(widthOf(bars[0])).toBe(50);
		expect(widthOf(bars[1])).toBe(100);
		expect(widthOf(bars[2])).toBe(50);
		expect(widthOf(bars[3])).toBe(0);
	});
});

describe('ProgressDashboard mount — curriculum summary bar gate', () => {
	let ProgressDashboard: typeof import('./ProgressDashboard.svelte').default;

	beforeEach(async () => {
		ProgressDashboard = (await import('./ProgressDashboard.svelte')).default;
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('totalLessons=0 (zero modules) → "X of N completed" label and curriculum-level bar are NOT rendered', async () => {
		const { render } = await import('@testing-library/svelte');
		const { container } = render(ProgressDashboard, {
			props: { modules: [], progress: {} }
		});

		// `{#if totalLessons > 0}` gates BOTH the label and the bar.
		expect(container.textContent).not.toContain('lessons completed');
		expect(container.querySelectorAll('[role="progressbar"]').length).toBe(0);
	});

	it('totalLessons=0 (one module with no lessons) → curriculum summary bar still gated off', async () => {
		const empty = makeModule('mod-empty', 0);
		const { render } = await import('@testing-library/svelte');
		const { container } = render(ProgressDashboard, {
			props: { modules: [empty], progress: {} }
		});

		expect(container.textContent).not.toContain('lessons completed');
		// The module card itself renders one ProgressBar (showing 0%);
		// what's gated off is the curriculum-level summary at the top.
		const bars = container.querySelectorAll('[role="progressbar"]');
		expect(bars.length).toBe(1);
	});
});

describe('ProgressDashboard mount — per-module action vs ✓ Complete', () => {
	let ProgressDashboard: typeof import('./ProgressDashboard.svelte').default;

	beforeEach(async () => {
		ProgressDashboard = (await import('./ProgressDashboard.svelte')).default;
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('complete module renders "✓ Complete"; incomplete sibling renders an action button', async () => {
		const m1 = makeModule('mod-01', 2); // fully complete
		const m2 = makeModule('mod-02', 2); // not started
		const progress = {
			'mod-01': makeProgress(m1, 2),
			'mod-02': makeProgress(m2, 0)
		};

		const { render } = await import('@testing-library/svelte');
		const { container } = render(ProgressDashboard, {
			props: { modules: [m1, m2], progress }
		});

		const cards = container.querySelectorAll('div.rounded-lg.border');
		expect(cards.length).toBe(2);

		const completeCard = cards[0] as HTMLElement;
		const incompleteCard = cards[1] as HTMLElement;

		expect(completeCard.textContent).toContain('✓ Complete');
		expect(completeCard.querySelector('button')).toBeNull();

		const actionBtn = incompleteCard.querySelector('button') as HTMLButtonElement | null;
		expect(actionBtn).not.toBeNull();
		// `not_started` rollup → "Start module →"; `in_progress` would
		// render "Continue →" (covered at the helper layer).
		expect(actionBtn!.textContent).toContain('Start module →');
	});
});
