// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// Story I.u — real-DOM mount coverage for `LessonList.svelte`. The helper
// `lessonStatusIcon` and `resolveLessonClick` cases in
// `module-list.test.ts` already pin the icon-mapping and lock-suppression
// logic; this file pins how that logic surfaces in the rendered DOM
// (icon glyphs, `aria-disabled`, `cursor-not-allowed`) and verifies the
// `goto` wiring on real button clicks.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import type {
	AssessmentDefinition,
	Lesson,
	LessonProgress,
	LessonStatus
} from '$lib/types/index.js';

const { gotoMock, currentPositionStore } = vi.hoisted(() => {
	// `vi.hoisted` runs before module-level imports, so `svelte/store`
	// has to be required dynamically here. A real writable is needed
	// (rather than a fake `{subscribe}`) so the Story J.t active-state
	// tests can push a position and have `LessonList` reactively pick
	// it up via the component's `$currentPosition` deref.
	// eslint-disable-next-line @typescript-eslint/no-require-imports
	const { writable } = require('svelte/store') as typeof import('svelte/store');
	type Pos = { moduleId: string; lessonId: string | null; assessmentId?: string | null } | null;
	return {
		gotoMock: vi.fn(),
		currentPositionStore: writable<Pos>(null)
	};
});

vi.mock('$app/navigation', () => ({ goto: gotoMock }));
vi.mock('$lib/stores/curriculum.js', () => ({
	currentPosition: currentPositionStore
}));

function makeLesson(id: string, title = id): Lesson {
	return { id, title, content_blocks: [] };
}

function makeProgress(
	moduleId: string,
	pairs: Record<string, LessonStatus>
): Record<string, LessonProgress> {
	const out: Record<string, LessonProgress> = {};
	for (const [lessonId, status] of Object.entries(pairs)) {
		out[lessonId] = { moduleId, lessonId, status, completedAt: null };
	}
	return out;
}

describe('LessonList mount — status icons render the correct glyph per status', () => {
	let LessonList: typeof import('./LessonList.svelte').default;

	beforeEach(async () => {
		gotoMock.mockReset();
		currentPositionStore.set(null);
		LessonList = (await import('./LessonList.svelte')).default;
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('renders ○ / … / ✓ / ◇ / … for not_started, in_progress, complete, optional, opened', () => {
		const lessons = [
			makeLesson('lesson-01'),
			makeLesson('lesson-02'),
			makeLesson('lesson-03'),
			makeLesson('lesson-04'),
			makeLesson('lesson-05')
		];
		const progress = makeProgress('mod-01', {
			'lesson-01': 'not_started',
			'lesson-02': 'in_progress',
			'lesson-03': 'complete',
			// `optional` is encoded both as a `LessonStatus` value (legacy)
			// and via the `optionalLessons` set (current code path). The
			// component's `statusIcon` strips the legacy value, so we use
			// the set as the source of truth for the ◇ icon.
			'lesson-04': 'not_started',
			'lesson-05': 'opened'
		});

		const { container } = render(LessonList, {
			props: {
				moduleId: 'mod-01',
				lessons,
				progress,
				optionalLessons: new Set<string>(['lesson-04']),
				lockedLessons: new Set<string>()
			}
		});

		const rows = container.querySelectorAll('ul > li');
		expect(rows.length).toBe(5);

		const iconText = (row: Element) => {
			const span = row.querySelector('span') as HTMLSpanElement;
			return span.textContent?.trim();
		};

		expect(iconText(rows[0])).toBe('○');
		expect(iconText(rows[1])).toBe('…');
		expect(iconText(rows[2])).toBe('✓');
		expect(iconText(rows[3])).toBe('◇');
		// `opened` shares the `…` glyph with `in_progress` by design
		// (FR-P15 / Story I.p).
		expect(iconText(rows[4])).toBe('…');
	});
});

describe('LessonList mount — role chip (Story J.b)', () => {
	let LessonList: typeof import('./LessonList.svelte').default;

	beforeEach(async () => {
		gotoMock.mockReset();
		currentPositionStore.set(null);
		LessonList = (await import('./LessonList.svelte')).default;
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('renders role chip with role text when lesson.meta.role is set', () => {
		const lessons: Lesson[] = [
			{
				id: 'lesson-01',
				title: 'L1',
				content_blocks: [],
				meta: { role: 'opener' }
			}
		];
		const { container } = render(LessonList, {
			props: {
				moduleId: 'mod-01',
				lessons,
				progress: {},
				optionalLessons: new Set<string>(),
				lockedLessons: new Set<string>()
			}
		});

		const chip = container.querySelector('[data-testid="lesson-role-chip"]');
		expect(chip).not.toBeNull();
		expect(chip?.textContent?.trim()).toBe('opener');
	});

	it('omits role chip when lesson.meta is undefined', () => {
		const lessons: Lesson[] = [makeLesson('lesson-01')];
		const { container } = render(LessonList, {
			props: {
				moduleId: 'mod-01',
				lessons,
				progress: {},
				optionalLessons: new Set<string>(),
				lockedLessons: new Set<string>()
			}
		});

		const chip = container.querySelector('[data-testid="lesson-role-chip"]');
		expect(chip).toBeNull();
	});

	it('omits role chip when lesson.meta is set but role is unset', () => {
		const lessons: Lesson[] = [
			{ id: 'lesson-01', title: 'L1', content_blocks: [], meta: {} }
		];
		const { container } = render(LessonList, {
			props: {
				moduleId: 'mod-01',
				lessons,
				progress: {},
				optionalLessons: new Set<string>(),
				lockedLessons: new Set<string>()
			}
		});

		const chip = container.querySelector('[data-testid="lesson-role-chip"]');
		expect(chip).toBeNull();
	});
});

describe('LessonList mount — assessment rows (Story J.f)', () => {
	let LessonList: typeof import('./LessonList.svelte').default;

	beforeEach(async () => {
		gotoMock.mockReset();
		currentPositionStore.set(null);
		LessonList = (await import('./LessonList.svelte')).default;
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	function makeAssessment(
		role: string,
		position: AssessmentDefinition['position'],
		pass_threshold: number | null = null
	): AssessmentDefinition {
		return {
			id: role,
			role,
			position,
			source: 'quizazz',
			ref: `a/${role}.yml`,
			pass_threshold,
			content: { assessmentName: role, tree: [], questions: [] }
		};
	}

	it('module with no assessments renders only lesson rows', () => {
		const lessons: Lesson[] = [makeLesson('lesson-01')];
		const { container } = render(LessonList, {
			props: {
				moduleId: 'mod-01',
				lessons,
				progress: {},
				optionalLessons: new Set<string>(),
				lockedLessons: new Set<string>()
			}
		});
		expect(container.querySelectorAll('[data-testid="assessment-row"]')).toHaveLength(0);
	});

	it('renders one assessment row when only `pre` is present', () => {
		const { container } = render(LessonList, {
			props: {
				moduleId: 'mod-01',
				lessons: [makeLesson('lesson-01')],
				assessments: [makeAssessment('pre', 'before_lessons')],
				progress: {},
				optionalLessons: new Set<string>(),
				lockedLessons: new Set<string>()
			}
		});
		const rows = container.querySelectorAll('[data-testid="assessment-row"]');
		expect(rows).toHaveLength(1);
		expect(rows[0].getAttribute('data-role')).toBe('pre');
		expect(rows[0].textContent).toContain('Pre Assessment');
	});

	it('renders three assessment rows interleaved with lessons in DOM order', () => {
		const { container } = render(LessonList, {
			props: {
				moduleId: 'mod-01',
				lessons: [makeLesson('lesson-01'), makeLesson('lesson-02')],
				assessments: [
					makeAssessment('pre', 'before_lessons'),
					makeAssessment('practice', { before_lesson: 'lesson-02' }),
					makeAssessment('post', 'after_lessons', 0.8)
				],
				progress: {},
				optionalLessons: new Set<string>(),
				lockedLessons: new Set<string>()
			}
		});
		const items = Array.from(container.querySelectorAll('ul > li')).map((li) => {
			// Story J.t — assessment rows became `<li> > <button data-role>`;
			// look one level deeper for the role attribute.
			const role = li.querySelector('[data-role]')?.getAttribute('data-role');
			if (role) return `assess:${role}`;
			const titleEl = li.querySelector('button span:nth-child(2)');
			return `lesson:${titleEl?.textContent?.trim()}`;
		});
		expect(items).toEqual([
			'assess:pre',
			'lesson:lesson-01',
			'assess:practice',
			'lesson:lesson-02',
			'assess:post'
		]);
	});

	it('shows "X% to pass" annotation when pass_threshold is set', () => {
		const { container } = render(LessonList, {
			props: {
				moduleId: 'mod-01',
				lessons: [makeLesson('lesson-01')],
				assessments: [makeAssessment('post', 'after_lessons', 0.7)],
				progress: {},
				optionalLessons: new Set<string>(),
				lockedLessons: new Set<string>()
			}
		});
		const threshold = container.querySelector('[data-testid="assessment-threshold"]');
		expect(threshold).not.toBeNull();
		expect(threshold?.textContent?.trim()).toBe('70% to pass');
	});

	it('omits "X% to pass" annotation when pass_threshold is null', () => {
		const { container } = render(LessonList, {
			props: {
				moduleId: 'mod-01',
				lessons: [makeLesson('lesson-01')],
				assessments: [makeAssessment('pre', 'before_lessons', null)],
				progress: {},
				optionalLessons: new Set<string>(),
				lockedLessons: new Set<string>()
			}
		});
		expect(
			container.querySelector('[data-testid="assessment-threshold"]')
		).toBeNull();
	});
});

describe('LessonList mount — locked rows', () => {
	let LessonList: typeof import('./LessonList.svelte').default;

	beforeEach(async () => {
		gotoMock.mockReset();
		currentPositionStore.set(null);
		LessonList = (await import('./LessonList.svelte')).default;
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('locked row carries aria-disabled="true" and cursor-not-allowed; click does not invoke goto', () => {
		const lessons = [makeLesson('lesson-01')];
		const { container } = render(LessonList, {
			props: {
				moduleId: 'mod-01',
				lessons,
				progress: {},
				optionalLessons: new Set<string>(),
				lockedLessons: new Set<string>(['lesson-01'])
			}
		});

		const btn = container.querySelector('ul > li > button') as HTMLButtonElement;
		expect(btn.getAttribute('aria-disabled')).toBe('true');
		expect(btn.className).toContain('cursor-not-allowed');

		btn.click();
		expect(gotoMock).not.toHaveBeenCalled();
	});

	it('unlocked row click invokes goto with /${moduleId}/${lessonId}', () => {
		const lessons = [makeLesson('lesson-01'), makeLesson('lesson-02')];
		const { container } = render(LessonList, {
			props: {
				moduleId: 'mod-01',
				lessons,
				progress: {},
				optionalLessons: new Set<string>(),
				lockedLessons: new Set<string>()
			}
		});

		const buttons = container.querySelectorAll('ul > li > button');
		(buttons[1] as HTMLButtonElement).click();

		expect(gotoMock).toHaveBeenCalledTimes(1);
		expect(gotoMock).toHaveBeenCalledWith('/mod-01/lesson-02');
	});
});

describe('LessonList mount — clickable assessment rows (Story J.t)', () => {
	let LessonList: typeof import('./LessonList.svelte').default;

	function makeAssessment(
		id: string,
		role: string,
		position: AssessmentDefinition['position'],
		pass_threshold: number | null = null
	): AssessmentDefinition {
		return {
			id,
			role,
			position,
			source: 'quizazz',
			ref: `a/${id}.yml`,
			pass_threshold,
			content: { assessmentName: id, tree: [], questions: [] }
		};
	}

	beforeEach(async () => {
		gotoMock.mockReset();
		currentPositionStore.set(null);
		LessonList = (await import('./LessonList.svelte')).default;
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('renders the assessment row as a clickable <button> (not a static <li> chip)', () => {
		const { container } = render(LessonList, {
			props: {
				moduleId: 'mod-01',
				lessons: [makeLesson('lesson-01')],
				assessments: [makeAssessment('pre', 'pre', 'before_lessons')],
				progress: {},
				optionalLessons: new Set<string>(),
				lockedLessons: new Set<string>()
			}
		});
		const row = container.querySelector('[data-testid="assessment-row"]');
		expect(row).not.toBeNull();
		expect(row?.tagName.toLowerCase()).toBe('button');
	});

	it('click navigates to `/${moduleId}/assessment/${assessmentId}`', () => {
		const { container } = render(LessonList, {
			props: {
				moduleId: 'mod-01',
				lessons: [makeLesson('lesson-01')],
				assessments: [makeAssessment('practice-2', 'practice', { after_lesson: 'lesson-01' })],
				progress: {},
				optionalLessons: new Set<string>(),
				lockedLessons: new Set<string>()
			}
		});
		const btn = container.querySelector(
			'[data-testid="assessment-row"]'
		) as HTMLButtonElement;
		btn.click();
		expect(gotoMock).toHaveBeenCalledTimes(1);
		expect(gotoMock).toHaveBeenCalledWith('/mod-01/assessment/practice-2');
	});

	it('active state (amber palette) renders when $currentPosition matches moduleId + assessmentId', () => {
		currentPositionStore.set({ moduleId: 'mod-01', lessonId: null, assessmentId: 'pre' });
		const { container } = render(LessonList, {
			props: {
				moduleId: 'mod-01',
				lessons: [makeLesson('lesson-01')],
				assessments: [
					makeAssessment('pre', 'pre', 'before_lessons'),
					makeAssessment('post', 'post', 'after_lessons', 0.8)
				],
				progress: {},
				optionalLessons: new Set<string>(),
				lockedLessons: new Set<string>()
			}
		});
		const rows = container.querySelectorAll('[data-testid="assessment-row"]');
		// First row matches — should be amber.
		expect(rows[0].className).toContain('bg-amber-100');
		expect(rows[0].className).toContain('text-amber-800');
		// Second row does not match — should not be amber.
		expect(rows[1].className).not.toContain('bg-amber-100');
	});

	it('inactive assessment row falls back to the default gray palette', () => {
		const { container } = render(LessonList, {
			props: {
				moduleId: 'mod-01',
				lessons: [makeLesson('lesson-01')],
				assessments: [makeAssessment('pre', 'pre', 'before_lessons')],
				progress: {},
				optionalLessons: new Set<string>(),
				lockedLessons: new Set<string>()
			}
		});
		const btn = container.querySelector(
			'[data-testid="assessment-row"]'
		) as HTMLButtonElement;
		expect(btn.className).toContain('text-gray-700');
		expect(btn.className).not.toContain('bg-amber-100');
	});

	it('locked appearance: aria-disabled="true" + cursor-not-allowed + grey palette; click does not navigate', () => {
		const { container } = render(LessonList, {
			props: {
				moduleId: 'mod-01',
				lessons: [makeLesson('lesson-01')],
				assessments: [makeAssessment('pre', 'pre', 'before_lessons')],
				progress: {},
				optionalLessons: new Set<string>(),
				lockedLessons: new Set<string>(),
				lockedAssessments: new Set(['pre'])
			}
		});
		const btn = container.querySelector(
			'[data-testid="assessment-row"]'
		) as HTMLButtonElement;
		expect(btn.getAttribute('aria-disabled')).toBe('true');
		expect(btn.className).toContain('cursor-not-allowed');
		expect(btn.className).toContain('text-gray-300');

		btn.click();
		expect(gotoMock).not.toHaveBeenCalled();
	});

	it('lockedAssessments default (omitted prop) leaves all assessment rows clickable', () => {
		const { container } = render(LessonList, {
			props: {
				moduleId: 'mod-01',
				lessons: [makeLesson('lesson-01')],
				assessments: [makeAssessment('pre', 'pre', 'before_lessons')],
				progress: {},
				optionalLessons: new Set<string>(),
				lockedLessons: new Set<string>()
				// `lockedAssessments` omitted — defaults to `new Set()` per Story J.t.
			}
		});
		const btn = container.querySelector(
			'[data-testid="assessment-row"]'
		) as HTMLButtonElement;
		expect(btn.getAttribute('aria-disabled')).toBe('false');
		expect(btn.className).not.toContain('cursor-not-allowed');
	});
});
