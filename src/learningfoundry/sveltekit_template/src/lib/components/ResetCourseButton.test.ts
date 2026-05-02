// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// Story I.u — real-DOM mount coverage for `ResetCourseButton.svelte`.
// Pre-Story I.u this file ran an inline copy of the click-handler against
// mocks because Svelte 5 component mounts weren't wired up. With the
// resolve-conditions config from Story I.q in place, the assertions now
// run against a real mount; the inline copy below stays as documentation
// so a reader can see the contract the component is meant to satisfy
// without reading the .svelte file.
//
//   async function clickHandler(disabled, confirmFn):
//     if (disabled) return;
//     if (!confirmFn(PROMPT)) return;
//     await resetProgress();
//     currentPosition.set(null);
//     await invalidateProgress($curriculum);
//     await goto('/');
//
// The branches:
//   - disabled → no DB writes, no goto, confirm not even prompted
//   - enabled + cancelled confirm → no DB writes, no goto
//   - enabled + accepted confirm → reset → set(null) → invalidate → goto
//     in that order; FR-P14 ordering is what makes the sidebar collapse
//     before the route change.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { resetMock, invalidateMock, gotoMock, setPosition } = vi.hoisted(() => ({
	resetMock: vi.fn().mockResolvedValue(undefined),
	invalidateMock: vi.fn().mockResolvedValue(undefined),
	gotoMock: vi.fn().mockResolvedValue(undefined),
	setPosition: vi.fn()
}));

vi.mock('$app/navigation', () => ({ goto: gotoMock }));
vi.mock('$lib/db/index.js', () => ({ progressRepo: { resetProgress: resetMock } }));
vi.mock('$lib/stores/curriculum.js', () => ({
	curriculum: {
		subscribe: (fn: (v: null) => void) => {
			fn(null);
			return () => {};
		}
	},
	currentPosition: { set: setPosition }
}));
vi.mock('$lib/stores/progress.js', () => ({ invalidateProgress: invalidateMock }));

const PROMPT = 'Reset all progress for this curriculum? This cannot be undone.';

describe('ResetCourseButton mount — disabled branch', () => {
	let ResetCourseButton: typeof import('./ResetCourseButton.svelte').default;

	beforeEach(async () => {
		resetMock.mockClear();
		invalidateMock.mockClear();
		gotoMock.mockClear();
		setPosition.mockClear();
		ResetCourseButton = (await import('./ResetCourseButton.svelte')).default;
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('disabled=true → rendered button has `disabled` attribute, `cursor-not-allowed text-gray-300` classes; click does not invoke handler', async () => {
		const { render } = await import('@testing-library/svelte');
		const confirmFn = vi.fn(() => true);
		const { container } = render(ResetCourseButton, {
			props: { disabled: true, confirmFn }
		});

		const btn = container.querySelector('button') as HTMLButtonElement;
		expect(btn.disabled).toBe(true);
		expect(btn.className).toContain('cursor-not-allowed');
		expect(btn.className).toContain('text-gray-300');

		btn.click();
		// `disabled` attribute on a real <button> blocks the synthetic click
		// event from firing the handler; resetProgress must remain unseen.
		expect(confirmFn).not.toHaveBeenCalled();
		expect(resetMock).not.toHaveBeenCalled();
		expect(setPosition).not.toHaveBeenCalled();
		expect(invalidateMock).not.toHaveBeenCalled();
		expect(gotoMock).not.toHaveBeenCalled();
	});
});

describe('ResetCourseButton mount — enabled + cancelled confirm', () => {
	let ResetCourseButton: typeof import('./ResetCourseButton.svelte').default;

	beforeEach(async () => {
		resetMock.mockClear();
		invalidateMock.mockClear();
		gotoMock.mockClear();
		setPosition.mockClear();
		ResetCourseButton = (await import('./ResetCourseButton.svelte')).default;
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('disabled=false + confirmFn returns false → confirm prompted, but no reset / set / invalidate / goto', async () => {
		const { render } = await import('@testing-library/svelte');
		const confirmFn = vi.fn(() => false);
		const { container } = render(ResetCourseButton, {
			props: { disabled: false, confirmFn }
		});

		const btn = container.querySelector('button') as HTMLButtonElement;
		btn.click();

		expect(confirmFn).toHaveBeenCalledTimes(1);
		expect(confirmFn).toHaveBeenCalledWith(PROMPT);
		expect(resetMock).not.toHaveBeenCalled();
		expect(setPosition).not.toHaveBeenCalled();
		expect(invalidateMock).not.toHaveBeenCalled();
		expect(gotoMock).not.toHaveBeenCalled();
	});
});

describe('ResetCourseButton mount — enabled + accepted confirm (FR-P14 ordering)', () => {
	let ResetCourseButton: typeof import('./ResetCourseButton.svelte').default;

	beforeEach(async () => {
		resetMock.mockClear();
		invalidateMock.mockClear();
		gotoMock.mockClear();
		setPosition.mockClear();
		ResetCourseButton = (await import('./ResetCourseButton.svelte')).default;
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('disabled=false + confirmFn returns true → resetProgress → currentPosition.set(null) → invalidateProgress → goto("/") in that order', async () => {
		const { render } = await import('@testing-library/svelte');
		const confirmFn = vi.fn(() => true);
		const { container } = render(ResetCourseButton, {
			props: { disabled: false, confirmFn }
		});

		const btn = container.querySelector('button') as HTMLButtonElement;
		btn.click();

		// click() schedules the async handler — let microtasks settle.
		for (let i = 0; i < 6; i += 1) await Promise.resolve();

		expect(resetMock).toHaveBeenCalledTimes(1);
		expect(setPosition).toHaveBeenCalledWith(null);
		expect(invalidateMock).toHaveBeenCalledTimes(1);
		expect(gotoMock).toHaveBeenCalledWith('/');

		// Ordering check via mock invocation order: reset → set → invalidate → goto.
		const order = [
			resetMock.mock.invocationCallOrder[0],
			setPosition.mock.invocationCallOrder[0],
			invalidateMock.mock.invocationCallOrder[0],
			gotoMock.mock.invocationCallOrder[0]
		];
		expect(order).toEqual([...order].sort((a, b) => a - b));
	});
});
