// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lessonHref, resolveGoNext, resolveGoPrev } from './navigation.helpers.js';

describe('resolveGoNext (Next/Finish button)', () => {
	it('routes to /{module}/{lesson} when there is a next lesson', () => {
		const action = resolveGoNext(false, { moduleId: 'mod-01', lessonId: 'lesson-02' });
		expect(action).toEqual({ kind: 'goto', url: '/mod-01/lesson-02' });
	});

	it('routes to / when next is null (Finish on last lesson) and signals position-clear', () => {
		const action = resolveGoNext(false, null);
		expect(action).toEqual({ kind: 'goto', url: '/', clearPosition: true });
	});

	it('does not signal position-clear when there is a next lesson', () => {
		const action = resolveGoNext(false, { moduleId: 'mod-01', lessonId: 'lesson-02' });
		// `clearPosition` is omitted (or false-y) for in-curriculum navigation.
		expect(action.kind).toBe('goto');
		if (action.kind === 'goto') {
			expect(action.clearPosition).toBeFalsy();
		}
	});

	it('disabled state is a no-op even with a next lesson', () => {
		const action = resolveGoNext(true, { moduleId: 'mod-01', lessonId: 'lesson-02' });
		expect(action).toEqual({ kind: 'noop' });
	});

	it('disabled state is a no-op when next is null', () => {
		const action = resolveGoNext(true, null);
		expect(action).toEqual({ kind: 'noop' });
	});
});

describe('resolveGoPrev (Previous button)', () => {
	it('routes to /{module}/{lesson} when there is a previous lesson', () => {
		const action = resolveGoPrev({ moduleId: 'mod-01', lessonId: 'lesson-01' });
		expect(action).toEqual({ kind: 'goto', url: '/mod-01/lesson-01' });
	});

	it('no-op when prev is null (first lesson)', () => {
		expect(resolveGoPrev(null)).toEqual({ kind: 'noop' });
	});
});

describe('lessonHref', () => {
	it('formats /{module}/{lesson}', () => {
		expect(lessonHref('mod-01', 'lesson-01')).toBe('/mod-01/lesson-01');
	});
});

// ---------------------------------------------------------------------------
// Story I.u — real-DOM mount coverage. The helper cases above pin the pure
// decision logic; the cases below pin the markup (disabled attribute +
// classes) and the FR-P14 ordering contract on Finish (currentPosition.set
// MUST run before goto so the sidebar's auto-collapse $effect sees the
// cleared position before the route changes).
// ---------------------------------------------------------------------------

interface NavPosition {
	moduleId: string;
	lessonId: string;
}

const { gotoMock, currentPositionSet, nextValue, prevValue } = vi.hoisted(() => ({
	gotoMock: vi.fn(),
	currentPositionSet: vi.fn(),
	nextValue: { value: null as NavPosition | null },
	prevValue: { value: null as NavPosition | null }
}));

vi.mock('$app/navigation', () => ({ goto: gotoMock }));
vi.mock('$lib/stores/curriculum.js', () => {
	const noop = () => {};
	return {
		currentPosition: {
			subscribe: (fn: (v: null) => void) => {
				fn(null);
				return noop;
			},
			set: currentPositionSet
		},
		nextLesson: {
			subscribe: (fn: (v: NavPosition | null) => void) => {
				fn(nextValue.value);
				return noop;
			}
		},
		previousLesson: {
			subscribe: (fn: (v: NavPosition | null) => void) => {
				fn(prevValue.value);
				return noop;
			}
		}
	};
});

describe('Navigation mount — disabled state', () => {
	let Navigation: typeof import('./Navigation.svelte').default;

	beforeEach(async () => {
		gotoMock.mockReset();
		currentPositionSet.mockReset();
		nextValue.value = { moduleId: 'mod-01', lessonId: 'lesson-02' };
		prevValue.value = null;
		Navigation = (await import('./Navigation.svelte')).default;
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('disabled=true → Next button has native disabled attribute and opacity-50 cursor-not-allowed classes', async () => {
		const { render } = await import('@testing-library/svelte');
		const { container } = render(Navigation, { props: { disabled: true } });
		// Two buttons: Previous (left), Next/Finish (right).
		const buttons = container.querySelectorAll('button');
		const next = buttons[1] as HTMLButtonElement;
		expect(next.disabled).toBe(true);
		expect(next.className).toContain('opacity-50');
		expect(next.className).toContain('cursor-not-allowed');
	});
});

describe('Navigation mount — Next click (in-curriculum nav)', () => {
	let Navigation: typeof import('./Navigation.svelte').default;

	beforeEach(async () => {
		gotoMock.mockReset();
		currentPositionSet.mockReset();
		nextValue.value = { moduleId: 'mod-01', lessonId: 'lesson-02' };
		prevValue.value = null;
		Navigation = (await import('./Navigation.svelte')).default;
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('disabled=false + non-null nextLesson → click goto(path); currentPosition.set NOT called', async () => {
		const { render } = await import('@testing-library/svelte');
		const { container } = render(Navigation, { props: { disabled: false } });
		const buttons = container.querySelectorAll('button');
		(buttons[1] as HTMLButtonElement).click();

		expect(gotoMock).toHaveBeenCalledTimes(1);
		expect(gotoMock).toHaveBeenCalledWith('/mod-01/lesson-02');
		expect(currentPositionSet).not.toHaveBeenCalled();
	});
});

describe('Navigation mount — Finish click (FR-P14 ordering)', () => {
	let Navigation: typeof import('./Navigation.svelte').default;

	beforeEach(async () => {
		gotoMock.mockReset();
		currentPositionSet.mockReset();
		nextValue.value = null; // Finish state — last lesson in curriculum.
		prevValue.value = null;
		Navigation = (await import('./Navigation.svelte')).default;
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('nextLesson=null + click → currentPosition.set(null) runs BEFORE goto("/")', async () => {
		const { render } = await import('@testing-library/svelte');
		const { container } = render(Navigation, { props: { disabled: false } });
		const buttons = container.querySelectorAll('button');
		(buttons[1] as HTMLButtonElement).click();

		expect(currentPositionSet).toHaveBeenCalledWith(null);
		expect(gotoMock).toHaveBeenCalledWith('/');
		// FR-P14 ordering: clearing the position MUST happen before the
		// route change so the sidebar's auto-expand $effect collapses the
		// previously-active module before the next render.
		const setOrder = currentPositionSet.mock.invocationCallOrder[0];
		const gotoOrder = gotoMock.mock.invocationCallOrder[0];
		expect(setOrder).toBeLessThan(gotoOrder);
	});
});
