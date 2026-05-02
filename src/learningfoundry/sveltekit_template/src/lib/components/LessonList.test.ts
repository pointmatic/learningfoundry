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
import type { Lesson, LessonProgress, LessonStatus } from '$lib/types/index.js';

const { gotoMock } = vi.hoisted(() => ({ gotoMock: vi.fn() }));

vi.mock('$app/navigation', () => ({ goto: gotoMock }));
vi.mock('$lib/stores/curriculum.js', () => {
	const noop = () => {};
	return {
		currentPosition: {
			subscribe: (fn: (v: null) => void) => {
				fn(null);
				return noop;
			}
		}
	};
});

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
				optionalLessons: new Set(['lesson-04']),
				lockedLessons: new Set()
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

describe('LessonList mount — locked rows', () => {
	let LessonList: typeof import('./LessonList.svelte').default;

	beforeEach(async () => {
		gotoMock.mockReset();
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
				optionalLessons: new Set(),
				lockedLessons: new Set(['lesson-01'])
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
				optionalLessons: new Set(),
				lockedLessons: new Set()
			}
		});

		const buttons = container.querySelectorAll('ul > li > button');
		(buttons[1] as HTMLButtonElement).click();

		expect(gotoMock).toHaveBeenCalledTimes(1);
		expect(gotoMock).toHaveBeenCalledWith('/mod-01/lesson-02');
	});
});
