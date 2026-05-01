// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// Logic-level coverage for the Reset Course button. We don't mount the
// Svelte component (the existing test convention is to extract testable
// logic instead). Instead we validate the click-handler contract:
//
//   - disabled → no DB writes, no goto
//   - enabled + cancelled confirm → no DB writes, no goto
//   - enabled + accepted confirm → resetProgress + invalidateProgress + goto('/')
//
// These three branches are the meaningful failure modes; the Svelte
// rendering is a thin shell over them.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { resetMock, invalidateMock, gotoMock, setPosition } = vi.hoisted(() => ({
	resetMock: vi.fn().mockResolvedValue(undefined),
	invalidateMock: vi.fn().mockResolvedValue(undefined),
	gotoMock: vi.fn(),
	setPosition: vi.fn()
}));

vi.mock('$app/navigation', () => ({ goto: gotoMock }));
vi.mock('$lib/db/index.js', () => ({ resetProgress: resetMock }));
vi.mock('$lib/stores/curriculum.js', () => ({
	curriculum: { subscribe: (fn: (v: null) => void) => (fn(null), () => {}) },
	currentPosition: { set: setPosition }
}));
vi.mock('$lib/stores/progress.js', () => ({ invalidateProgress: invalidateMock }));

const PROMPT = 'Reset all progress for this curriculum? This cannot be undone.';

/**
 * Inline copy of the click-handler logic in `ResetCourseButton.svelte`.
 * Kept in lockstep with the component; if you change the component, mirror
 * the change here.
 */
async function clickHandler(
	disabled: boolean,
	confirmFn: (msg: string) => boolean
): Promise<void> {
	const { resetProgress } = await import('$lib/db/index.js');
	const { currentPosition, curriculum } = await import('$lib/stores/curriculum.js');
	const { invalidateProgress } = await import('$lib/stores/progress.js');
	const { goto } = await import('$app/navigation');
	if (disabled) return;
	if (!confirmFn(PROMPT)) return;
	await resetProgress();
	currentPosition.set(null);
	let cur = null;
	curriculum.subscribe((v: unknown) => (cur = v as null))();
	await invalidateProgress(cur);
	await goto('/');
}

describe('ResetCourseButton click handler', () => {
	beforeEach(() => {
		resetMock.mockClear();
		invalidateMock.mockClear();
		gotoMock.mockClear();
		setPosition.mockClear();
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('disabled → no reset, no navigation', async () => {
		const confirmFn = vi.fn(() => true);
		await clickHandler(true, confirmFn);
		expect(confirmFn).not.toHaveBeenCalled();
		expect(resetMock).not.toHaveBeenCalled();
		expect(setPosition).not.toHaveBeenCalled();
		expect(invalidateMock).not.toHaveBeenCalled();
		expect(gotoMock).not.toHaveBeenCalled();
	});

	it('enabled + cancelled confirm → no reset, no navigation', async () => {
		const confirmFn = vi.fn(() => false);
		await clickHandler(false, confirmFn);
		expect(confirmFn).toHaveBeenCalledOnce();
		expect(resetMock).not.toHaveBeenCalled();
		expect(setPosition).not.toHaveBeenCalled();
		expect(gotoMock).not.toHaveBeenCalled();
	});

	it('enabled + accepted confirm → resets, clears position, invalidates, navigates home', async () => {
		const confirmFn = vi.fn(() => true);
		await clickHandler(false, confirmFn);
		expect(resetMock).toHaveBeenCalledOnce();
		expect(setPosition).toHaveBeenCalledWith(null);
		expect(invalidateMock).toHaveBeenCalledOnce();
		expect(gotoMock).toHaveBeenCalledWith('/');
	});
});
